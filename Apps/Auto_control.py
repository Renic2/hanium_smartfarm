# =================================================================================
# Auto_control.py
# 시스템의 자동 제어 로직 담당
# 별도의 스레드에서 주기적 실행, 온도와 토양 습도 관리를 중점으로 한다.
# =================================================================================


# 외부 모듈 호출
import threading
import time
import json

# 내부 모듈 호출
import Config
from Utility import log, PID
from _System_ import SystemState
from Arduino_control import HardwareController

class AutoController:
    def __init__ (self, state: SystemState, hardware: HardwareController):
        self.state = state
        self.hardware = hardware
        self.data = self.state.get_all_data()

        # PID 제어기 쵝화
        self.pid = PID(Config.PID_KP, Config.PID_KI, Config.PID_KD, self.data["TARGET"]["TARGET_TEMP"])
        self.stop_event = threading.Event()
        self.control_interval = 2

    # 자동 제어 로직을 주기적으로 실행하는 메인 루프
    def _control_loop_worker(self):
        while not self.stop_event.is_set():
            try:
                # 현재 상태와 목표값 가져오기
                self.data = self.state.get_all_data()
                self.sensors = self.data["SENSOR"]
                self.targets = self.data["TARGET"]

                # 시스템 모드 확인
                if self.data["MODE"] != "AUTO":
                    time.sleep(self.control_interval)
                    continue

                # 온도 제어
                self.pid.setpoint = float(self.targets["TARGET_TEMP"])
                pid_output = self.pid.compute(float(self.sensors["TEMP"]))

                # PID에 따라 온도를 조절하는 액추에이터
                if pid_output > 2: # 온도가 낮을 떄.
                    self.data["ACTUATOR"]["FAN"] = 0
                    self.data["ACTUATOR"]["HEAT_PANNEL"] = 1

                elif pid_output < -2: # 온도가 높을 떄.
                    self.data["ACTUATOR"]["FAN"] = 200
                    self.data["ACTUATOR"]["HEAT_PANNEL"] = 0

                else: # 온도가 목표 근처일 때
                    self.data["ACTUATOR"]["FAN"] = 0
                    self.data["ACTUATOR"]["HEAT_PANNEL"] = 0

                # 토양 습도 제어
                if float(self.sensors["SOIL"]) < float(self.targets["TARGET_SOIL_MOISTURE"]):
                    log.info("[제어] 토양 습도가 낮습니다. 펌프를 작동합니다.")
                    self.data["ACTUATOR"]["PUMP"] = 255
                    time.sleep(2)
                    log.info("[제어] 펌프를 제어 종료.")
                    self.data["ACTUATOR"]["PUMP"] = 0

                self.state._write_state(self.data)

            except Exception as e:
                log.error(f"[자동 제어] 자동 제어 중 에러가 발생하였습니다: {e}")

            time.sleep(self.control_interval)

    # 자동 제어 스레드 시작
    def start(self):
        log.info("자동 제어 스레드를 시작합니다.")
        threading.Thread(target=self._control_loop_worker, daemon=True).start()
        log.info("자동 제어가 진행중입니다.")

    def stop(self):
        log.info("자동 제어를 정지합니다.")
        self.stop_event.set()
        log.info("자동 제어가 정지되었습니다.")