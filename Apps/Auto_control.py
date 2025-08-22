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

class AutoController:
    def __init__(self, state: SystemState, hardware: None): # hardware 인자 제거
        self.state = state
        self.last_pump_time = 0
        
        # PID 제어기 초기화
        current_data = self.state.get_all_data()
        self.pid = PID(Config.PID_KP, Config.PID_KI, Config.PID_KD, current_data["TARGET"]["TARGET_TEMP"])
        
        self.stop_event = threading.Event()
        self.control_interval = Config.CONTROL_INTERVAL

    def _control_loop_worker(self):
        while not self.stop_event.is_set():
            try:
                current_data = self.state.get_all_data()
                sensors = current_data["SENSOR"]
                targets = current_data["TARGET"]
                actuators = current_data["ACTUATOR"]
                
                if current_data.get("MODE") != "AUTO":
                    time.sleep(self.control_interval)
                    continue

                # --- 온도 제어 ---
                self.pid.setpoint = float(targets["TARGET_TEMP"])
                pid_output = self.pid.compute(float(sensors["TEMP"]))

                if pid_output > 2:  # 온도가 낮을 때
                    actuators["FAN"] = 0
                    actuators["HEAT_PANNEL"] = 1
                elif pid_output < -2:  # 온도가 높을 때
                    actuators["FAN"] = 200
                    actuators["HEAT_PANNEL"] = 0
                else:  # 온도가 적정할 때
                    actuators["FAN"] = 0
                    actuators["HEAT_PANNEL"] = 0
                
                # --- 토양 습도 제어 (non-blocking 방식으로 수정) ---
                current_time = time.time()
                is_pumping = actuators.get("PUMP", 0) > 0

                # 펌프가 꺼져있고, 습도가 낮고, 마지막으로 물 준 지 10초가 지났을 때
                if not is_pumping and float(sensors["SOIL"]) < float(targets["TARGET_SOIL_MOISTURE"]) and (current_time - self.last_pump_time > 10):
                    log.info("[Auto Control] Soil moisture low. Activating PUMP.")
                    actuators["PUMP"] = 255
                    self.last_pump_time = current_time # 펌프 켠 시간 기록
                
                # 펌프가 켜져있고, 2초가 지났을 때
                elif is_pumping and (current_time - self.last_pump_time > 2):
                    log.info("[Auto Control] Stopping PUMP.")
                    actuators["PUMP"] = 0
                
                # ★★★★★ 핵심 수정 ★★★★★
                # 모든 제어 로직이 끝난 후, 최종 상태를 파일에 한 번만 기록합니다.
                self.state.update_values({"ACTUATOR": actuators})

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