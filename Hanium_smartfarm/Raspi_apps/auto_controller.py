# -----------------------------------------------------------------------
# auto_controller.py
# 시스템의 자동 제어 로직 담당
# 별도의 스레드에서 주기적으로 실행되며, 온도와 토양 습도 관리
# -----------------------------------------------------------------------

import threading
import time
from util import log, PID
import config
from system_state import SystemState
from hardware_control import HardwareController

class AutoController:
    def __init__(self, state: SystemState, hardware: HardwareController):
        self.state = state
        self.hardware = hardware

        # PID 제어기 초기화
        self.pid = PID(config.PID_KP, config.PID_KI,
                       config.PID_KD, config.TARGET_TEMP)
        
        self.stop_event = threading.Event()
        self.control_interval = 5 # 제어 루프 실행 간격 (초)

    def _control_loop_worker(self):
        # 자동 제어 로직을 주기적으로 실행하는 메인 루프
        while not self.stop_event.is_set():
            try:
                # 현재 상태와 목표값 가져오기
                full_state = self.state.get_full_state()
                current_sensors = full_state["sensors"]
                current_targets = full_state["targets"]

                # 시스템 모드 확인 (AUTO 모드일 때만 적용)
                if full_state["mode"] != "AUTO":
                    time.sleep(self.control_interval)
                    continue

                # 온도 제어
                self.pid.setpoint = current_targets["TARGET_TEMP"]
                pid_output = self.pid.compute(current_sensors["temp"])

                # PID 출력값에 따른 팬/히터 PWM 제어
                if pid_output > 2: # 목표보다 온도가 너무 낮을 때
                    self.hardware.send_command("HEAT_PANNEL", 1) # 히터 켜기
                    self.hardware.send_command("FAN", 0)         # 팬 끄기
                
                elif pid_output < -2: # 목표보다 온도가 너무 높을 때
                    self.hardware.send_command("HEAT_PANNEL", 0) # 히터 끄기
                    self.hardware.send_command("FAN", 200)       # 팬 켜기 (PWM 200)
                
                else: # 목표 온도 범위 근처일 때
                    self.hardware.send_command("HEAT_PANNEL", 0)
                    self.hardware.send_command("FAN", 0)

                # 토양 습도 제어
                if current_sensors["soil"] < current_targets["TARGET_SOIL_MOISTURE"]:
                    log.info(f"[CONTROL] Soil moisture low. Activating PUMP.")
                    self.hardware.send_command("PUMP", 255) # 펌프 최대 세기로 작동
                    time.sleep(2) # 2초간 물 주기
                    self.hardware.send_command("PUMP", 0)   # 펌프 끄기

            except Exception as e:
                log.error(f"Error in auto control loop: {e}")

            time.sleep(self.control_interval)
        
    def start(self):
        """자동 제어 스레드를 시작합니다."""
        log.info("Starting auto-controller thread...")
        threading.Thread(target=self._control_loop_worker, daemon=True).start()
        log.info("Auto-controller is running.")

    def stop(self):
        """자동 제어 스레드를 종료합니다."""
        log.info("Stopping auto-controller...")
        self.stop_event.set()
        log.info("Auto-controller stopped.")