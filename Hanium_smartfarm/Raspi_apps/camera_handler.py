# -----------------------------------------------------------------------
# camera_handler.py
# CLI 카메라를 사용하여 사진을 촬영, 처리하는 모든 작업 담당
# -----------------------------------------------------------------------

import subprocess
import os
import time
from datetime import datetime
from util import log
from hardware_control import HardwareController
from aws_handler import AWSHandler

class CameraHandler:
    def __init__(self, hardware: HardwareController, aws: AWSHandler):
        self.hardware = hardware
        self.aws = aws

        # 사용자의 홈 디텍토리 경로를 찾아 카메라 실행 파일의 절대 경로 탐색
        home_dir = os.path.expanduser("~")
        self.camera_command_path = os.path.join(home_dir, "rpicam-apps/build/apps/rpicam-still")

    def capture_and_upload(self):
        # 사진 촬영을 위한 조명 제어, CLI 카메라 촬영 호 S3에 업로드
        log.info("Starting capture and upload sequence...")

        # 조명 제어
        self.hardware.send_command("GROW_LIGHT", 0)
        self.hardware.send_command("WHITE_LED", 1)

        # 파일 이름 생성 (예: 20250803_123000.jpg)
        timestamp = datetime.now.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}.jpg"
        # /tmp 디렉토리는 재부팅 시 내용이 사라지는 임시 저장 공간으로 적합합니다.
        local_filepath = f"/tmp/{filename}" 

        try:
            # 조명이 안정화될 시간을 줍니다.
            time.sleep(2)

            # CLI 카메라 명령어 실행 (절대 경로 사용)
            command = [
                self.camera_command_path,
                "-o", local_filepath,
                "-t", "500",      # 셔터 누르기 전 0.5초 대기
                "--width", "1920",
                "--height", "1080",
                "--nopreview"     # 미리보기 창을 띄우지 않음
            ]
            
            log.info(f"Executing camera command: {' '.join(command)}")
            # check=True: 명령어 실패 시 CalledProcessError 발생
            subprocess.run(command, capture_output=True, text=True, check=True)
            log.info(f"Photo captured successfully and saved to {local_filepath}")

            # S3에 업로드
            s3_object_name = f"images/{filename}"
            self.aws.upload_to_s3(local_filepath, s3_object_name)

        except FileNotFoundError:
            log.error(f"Camera command not found at '{self.camera_command_path}'. Please check the path.")
        
        except subprocess.CalledProcessError as e:
            log.error(f"Camera command failed with exit code {e.returncode}: {e.stderr}")
        
        except Exception as e:
            log.error(f"An unexpected error occurred during capture sequence: {e}")
        
        finally:
            # 조명 원상 복구 (성공/실패 여부와 관계없이 항상 실행)
            log.info("Restoring light state...")
            self.hardware.send_command("WHITE_LED", 0)
            self.hardware.send_command("GROW_LIGHT", 1)
            
            # 로컬에 저장된 임시 파일 삭제
            if os.path.exists(local_filepath):
                try:
                    os.remove(local_filepath)
                    log.info(f"Removed temporary file: {local_filepath}")
                except OSError as e:
                    log.error(f"Error removing temporary file {local_filepath}: {e}")