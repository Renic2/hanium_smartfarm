import threading
import time
import subprocess
import os
from datetime import datetime
from Utility import log
from AWS_control import AWSHandler
from Arduino_control import HardwareController
from _System_ import SystemState

class CameraHandler:
    def __init__(self, state: SystemState, hardware: HardwareController, aws: AWSHandler):
        self.state = state
        self.hardware = hardware
        self.aws = aws
        self.stop_event = threading.Event()
        self.capture_interval = 300  # 5분

        home_dir = os.path.expanduser("~")
        self.camera_command_path = os.path.join(home_dir, "rpicam-apps/build/apps/rpicam-still")

    def _capture_loop(self):
        """5분마다 사진 촬영 및 업로드를 반복하는 메인 루프입니다."""
        while not self.stop_event.is_set():
            self.capture_and_upload()
            self.stop_event.wait(self.capture_interval)

    def capture_and_upload(self):
        """조명 상태를 저장 및 복원하며 안전하게 사진을 촬영하고 업로드합니다."""
        log.info("사진 촬영 시퀀스를 시작합니다...")

        # 1. 현재 조명 상태를 파일에서 직접 읽어와 저장
        current_data = self.state.get_all_data()
        original_actuators = current_data.get("ACTUATOR", {})
        original_grow_light = original_actuators.get("GROW_LIGHT", 0)
        original_white_led = original_actuators.get("WHITE_LED", 0)
        log.info(f"촬영 전 조명 상태 저장: 생장등={original_grow_light}, 백색등={original_white_led}")

        local_filepath = ""
        try:
            # 2. 사진 촬영을 위한 조명으로 변경 (*** 여기가 수정된 부분 ***)
            # send_command 대신 state.update_values 사용
            log.info("사진 촬영용 조명으로 변경합니다...")
            update_data_for_capture = {
                "ACTUATOR": {
                    "GROW_LIGHT": 0,
                    "WHITE_LED": 1
                }
            }
            self.state.update_values(update_data_for_capture)
            time.sleep(2)  # 조명이 안정화되고 Arduino가 상태를 반영할 때까지 대기

            # 3. 사진 촬영
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.jpg"
            local_filepath = f"/tmp/{filename}"

            command = [self.camera_command_path, "-o", local_filepath, "-t", "500", "--width", "1920", "--height", "1080", "--nopreview"]
            log.info(f"카메라 촬영 실행: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True, text=True)
            log.info(f"사진 촬영 성공: {local_filepath}")

            # 4. S3에 업로드
            s3_object_name = f"images/{filename}"
            self.aws.upload_to_s3(local_filepath, s3_object_name)

        except FileNotFoundError:
            log.error(f"카메라 실행 파일을 찾을 수 없습니다: '{self.camera_command_path}'")
        except subprocess.CalledProcessError as e:
            log.error(f"카메라 명령어 실행 실패: {e.stderr}")
        except Exception as e:
            log.error(f"사진 촬영 시퀀스 중 예기치 않은 오류 발생: {e}")
        finally:
            # 5. 조명을 원래 상태로 복원 (가장 중요!) (*** 여기가 수정된 부분 ***)
            log.info(f"조명 상태를 원래대로 복원합니다: 생장등={original_grow_light}, 백색등={original_white_led}")
            update_data_for_restore = {
                "ACTUATOR": {
                    "GROW_LIGHT": original_grow_light,
                    "WHITE_LED": original_white_led
                }
            }
            self.state.update_values(update_data_for_restore)
            
            # 임시 파일 삭제
            if local_filepath and os.path.exists(local_filepath):
                os.remove(local_filepath)
                log.info(f"임시 파일 삭제: {local_filepath}")
            
            log.info("사진 촬영 시퀀스를 종료합니다.")

    def start(self):
        log.info("주기적 사진 촬영 스레드를 시작합니다.")
        threading.Thread(target=self._capture_loop, daemon=True).start()
        log.info("사진 촬영 스레드가 실행 중입니다.")

    def stop(self):
        log.info("사진 촬영 스레드를 정지합니다.")
        self.stop_event.set()
        log.info("사진 촬영 스레드가 정지되었습니다.")