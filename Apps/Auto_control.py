# =================================================================================
# Auto_control.py
# 시스템의 자동 제어 로직 담당
# 별도의 스레드에서 주기적 실행, 온도와 토양 습도 관리를 중점으로 한다.
# =================================================================================

import threading
import time
from Utility import log, PID
import Config
from _System_ import SystemState
from Arduino_control import HardwareController

class AutoController:
    def __init__(self, state: SystemState, hardware: HardwareController):
        self.state = state
        self.hardware = hardware # hardware 객체를 다시 사용합니다.
        self.last_pump_time = 0
        
        current_data = self.state.get_all_data()
        self.pid = PID(Config.PID_KP, Config.PID_KI, Config.PID_KD, current_data["TARGET"]["TARGET_TEMP"])
        
        self.stop_event = threading.Event()
        self.control_interval = Config.CONTROL_INTERVAL

    def _control_loop_worker(self):
        while not self.stop_event.is_set():
            try:
                current_data = self.state.get_all_data()
                
                if current_data.get("MODE") != "AUTO":
                    time.sleep(self.control_interval)
                    continue

                sensors = current_data["SENSOR"]
                targets = current_data["TARGET"]
                
                # --- 온도 제어 ---
                self.pid.setpoint = float(targets["TARGET_TEMP"])
                pid_output = self.pid.compute(float(sensors["TEMP"]))

                if pid_output > 2:
                    current_data["ACTUATOR"]["FAN"] = 0
                    current_data["ACTUATOR"]["HEAT_PANNEL"] = 1
                elif pid_output < -2:
                    current_data["ACTUATOR"]["FAN"] = 200
                    current_data["ACTUATOR"]["HEAT_PANNEL"] = 0
                else:
                    current_data["ACTUATOR"]["FAN"] = 0
                    current_data["ACTUATOR"]["HEAT_PANNEL"] = 0
                
                # --- 토양 습도 제어 (non-blocking 방식) ---
                current_time = time.time()
                is_pumping = current_data["ACTUATOR"].get("PUMP", 0) > 0

                if not is_pumping and float(sensors["SOIL"]) < float(targets["TARGET_SOIL_MOISTURE"]) and (current_time - self.last_pump_time > 10):
                    log.info("[Auto Control] Soil moisture low. Activating PUMP.")
                    current_data["ACTUATOR"]["PUMP"] = 255
                    self.last_pump_time = current_time
                
                elif is_pumping and (current_time - self.last_pump_time > 2):
                    log.info("[Auto Control] Stopping PUMP.")
                    current_data["ACTUATOR"]["PUMP"] = 0
                
                # ★★★ 핵심 수정: 변경된 모든 내용을 파일에 한 번에 저장 ★★★
                self.state._write_state(current_data)

            except Exception as e:
                log.error(f"[Auto Control] Error in control loop: {e}")

            time.sleep(self.control_interval)

    def start(self):
        log.info("자동 제어 스레드를 시작합니다.")
        threading.Thread(target=self._control_loop_worker, daemon=True).start()
        log.info("자동 제어가 진행중입니다.")

    def stop(self):
        log.info("자동 제어를 정지합니다.")
        self.stop_event.set()
        log.info("자동 제어가 정지되었습니다.")