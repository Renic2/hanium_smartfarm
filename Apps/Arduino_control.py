# =================================================================================
# Arduino_control.py (텍스트 파싱 최종본)
# 아두이노와의 시리얼 통신, 센서/액추에이터 제어 송수신
# =================================================================================
import serial
import serial.tools.list_ports
import threading
import time
import json # JSON 형식은 아니지만, 혹시 모를 로깅을 위해 유지

from Utility import log
import Config
from _System_ import SystemState

class HardwareController:
    def __init__(self, state: SystemState):
        self.state = state
        self.ser = None
        self.last_heartbeat_time = time.time()
        self.stop_event = threading.Event()
        self.reconnect_event = threading.Event()

    # ... (_find_serial_port, connect, trigger_reconnect, start, stop 메서드는 이전과 동일) ...
    def _find_serial_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.device or 'ACM' in port.device or 'COM' in port.device:
                log.info(f"아두이노 추정 포트 발견: {port.device}")
                return port.device
        return None
    
    def connect(self):
        while not self.stop_event.is_set():
            port = Config.SERIAL_PORT or self._find_serial_port()
            if port:
                try:
                    self.ser = serial.Serial(port, Config.BAUD_RATE, timeout=1)
                    log.info(f"성공적으로 아두이노가 포트에서 연결되었습니다: {port}")
                    self.reconnect_event.clear()
                    self.last_heartbeat_time = time.time()
                    return True
                except serial.SerialException as e:
                    log.warning(f"{port}에 연결을 실패했습니다: {e}")
            else:
                log.warning("연결할 시리얼 포트를 찾지 못하였습니다.")
            
            log.warning(f"{Config.RECONNECT_DELAY}초 후 재연결을 시도합니다.")
            time.sleep(Config.RECONNECT_DELAY)
        return False

    def _read_thread_worker(self):
        """(스레드 1) 아두이노로부터 텍스트 데이터를 읽고 상태를 처리합니다."""
        while not self.stop_event.is_set():
            if self.reconnect_event.is_set():
                time.sleep(1)
                continue

            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    
                    # ★★★ 핵심 수정 1: 텍스트 형식 파싱 ★★★
                    if line.startswith("SENSOR:"):
                        data_part = line[7:]  # "SENSOR:" 부분 제거
                        items = data_part.split(',')
                        
                        if len(items) == 4:
                            current_state = self.state.get_all_data()
                            # 아두이노가 보내는 순서: TEMP, SOIL, HUMID, LIGHT
                            current_state["SENSOR"]["TEMP"] = float(items[0])
                            current_state["SENSOR"]["SOIL"] = float(items[1])
                            current_state["SENSOR"]["HUMID"] = float(items[2])
                            current_state["SENSOR"]["LIGHT"] = float(items[3])
                            
                            self.state.write_state(current_state)
                            log.debug(f"센서 값 수신 및 업데이트 완료: {current_state['SENSOR']}")
                        else:
                            log.warning(f"수신한 센서 데이터 형식이 올바르지 않습니다: {line}")

                    elif line.startswith("HEARTBEAT:"):
                        self.last_heartbeat_time = time.time()
                        log.debug("HeartBeat 신호를 수신하였습니다.")

                except (UnicodeDecodeError, ValueError) as e:
                    log.warning(f"시리얼 데이터 처리 중 오류 발생: {e} | 원본 데이터: {line}")
            
            time.sleep(0.1)

    def _write_thread_worker(self):
        """(스레드 2) 주기적으로 최신 액추에이터 상태를 텍스트로 아두이노에 전송합니다."""
        while not self.stop_event.is_set():
            if not self.reconnect_event.is_set() and self.ser and self.ser.is_open:
                try:
                    actuator_data = self.state.get_all_data()["ACTUATOR"]
                    
                    # ★★★ 핵심 수정 2: 쉼표로 구분된 텍스트 형식으로 변경 ★★★
                    cmd_list = [
                        str(actuator_data.get("FAN", 0)),
                        str(actuator_data.get("PUMP", 0)),
                        str(actuator_data.get("HEAT_PANNEL", 0)),
                        str(actuator_data.get("GROW_LIGHT", 0)),
                        str(actuator_data.get("WHITE_LED", 0))
                    ]
                    
                    cmd_str = ','.join(cmd_list) + "\n"
                    self.ser.write(cmd_str.encode('utf-8'))
                    log.debug(f"액추에이터 명령 전송: {cmd_str.strip()}")

                except Exception as e:
                    log.warning(f"[아두이노] 액추에이터 전송에 실패하였습니다: {e}")
            
            time.sleep(Config.CONTROL_INTERVAL)

    def _watchdog_thread(self):
        """(스레드 3) Heartbeat를 감시하여 연결 상태를 확인합니다."""
        while not self.stop_event.is_set():
            if not self.reconnect_event.is_set():
                if time.time() - self.last_heartbeat_time > Config.HEARTBEAT_TIMEOUT:
                    log.warning("지정된 시간 내에 HeartBeat이 수신되지 않았습니다. 재연결을 시작합니다.")
                    self.trigger_reconnect()
            time.sleep(1)

    def trigger_reconnect(self):
        if self.reconnect_event.is_set():
            return
        
        log.info("재연결 과정을 시작합니다.")
        self.reconnect_event.set()

        if self.ser:
            try:
                self.ser.close()
            except Exception as e:
                log.error(f"시리얼 포트 종료 중 오류 발생: {e}")
            finally:
                self.ser = None

        reconnect_thread = threading.Thread(target=self.connect, daemon=True)
        reconnect_thread.start()

    def start(self):
        log.info("하드웨어 컨트롤러를 시작합니다.")
        if not self.connect():
            log.error("초기 연결에 실패하였습니다. 프로그램을 종료합니다.")
            return
        threading.Thread(target=self._read_thread_worker, daemon=True).start()
        threading.Thread(target=self._write_thread_worker, daemon=True).start()
        threading.Thread(target=self._watchdog_thread, daemon=True).start()
        log.info("하드웨어 컨트롤러의 모든 스레드가 실행 중입니다.")

    def stop(self):
        log.info("하드웨어 컨트롤러를 종료합니다.")
        self.stop_event.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
        log.info("하드웨어 컨트롤러가 정지되었습니다.")
