# =================================================================================
# Arduino_control.py (JSON 통신 수정본)
# =================================================================================
import serial
import serial.tools.list_ports
import threading
import time
import json

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
        """(스레드 1) 아두이노로부터 JSON 데이터를 읽고 상태를 처리합니다."""
        while not self.stop_event.is_set():
            if self.reconnect_event.is_set():
                time.sleep(1)
                continue

            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    
                    # ★★★ 핵심 수정 1: 수신한 데이터를 JSON으로 파싱 ★★★
                    data = json.loads(line)
                    data_type = data.get("TYPE")

                    if data_type == "SENSOR":
                        # SENSOR 데이터를 value.json에 업데이트
                        current_state = self.state.get_all_data()
                        current_state["SENSOR"] = {
                            "TEMP": data.get("TEMP"),
                            "HUMID": data.get("HUMID"),
                            "SOIL": data.get("SOIL"),
                            "LIGHT": data.get("LIGHT")
                        }
                        self.state.write_state(current_state)
                        log.debug(f"센서 값 수신 및 업데이트 완료: {current_state['SENSOR']}")

                    elif data_type == "HEARTBEAT":
                        self.last_heartbeat_time = time.time()
                        log.debug("HeartBeat 신호를 수신하였습니다.")

                except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
                    log.warning(f"아두이노 데이터 처리 중 오류 발생: {e} | 원본 데이터: {line}")
            
            time.sleep(0.1)

    def _write_thread_worker(self):
        """(스레드 2) 주기적으로 최신 액추에이터 상태를 아두이노로 전송합니다."""
        # ★★★ 핵심 수정 2: 제어 루프 추가 ★★★
        while not self.stop_event.is_set():
            if not self.reconnect_event.is_set() and self.ser and self.ser.is_open:
                try:
                    actuator_data = self.state.get_all_data()["ACTUATOR"]
                    
                    # 아두이노로 보낼 JSON 객체 생성
                    command_to_send = {
                        "DEVICE": "ALL", # 모든 장치 상태를 한번에 보낸다는 의미
                        "VALUE": {
                            "FAN": actuator_data.get("FAN", 0),
                            "PUMP": actuator_data.get("PUMP", 0),
                            "HEAT_PANNEL": actuator_data.get("HEAT_PANNEL", 0),
                            "GROW_LIGHT": actuator_data.get("GROW_LIGHT", 0),
                            "WHITE_LED": actuator_data.get("WHITE_LED", 0)
                        }
                    }
                    
                    # JSON 문자열로 변환하여 전송
                    cmd_str = json.dumps(command_to_send) + "\n"
                    self.ser.write(cmd_str.encode('utf-8'))
                    log.debug(f"액추에이터 명령 전송: {command_to_send['VALUE']}")

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
        """아두이노와의 재연결 과정을 시작합니다."""
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
        """하드웨어 제어에 필요한 모든 스레드를 시작합니다."""
        log.info("하드웨어 컨트롤러를 시작합니다.")
        
        if not self.connect():
            log.error("초기 연결에 실패하였습니다. 프로그램을 종료합니다.")
            return
        
        threading.Thread(target=self._read_thread_worker, daemon=True).start()
        threading.Thread(target=self._write_thread_worker, daemon=True).start()
        threading.Thread(target=self._watchdog_thread, daemon=True).start()
        
        log.info("하드웨어 컨트롤러의 모든 스레드가 실행 중입니다.")

    def stop(self):
        """하드웨어 제어를 안전하게 종료합니다."""
        log.info("하드웨어 컨트롤러를 종료합니다.")
        self.stop_event.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
        log.info("하드웨어 컨트롤러가 정지되었습니다.")
