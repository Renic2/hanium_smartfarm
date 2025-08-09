# =================================================================================
# Arduino_control.py
# 아두이노와의 시리얼 통신, 센서/액추에이터 제어 송수신
# Heartbeat와 Watchdog를 통한 안정적인 유지를 목표로 한다.
# =================================================================================

# 외부 모듈 호출
import serial
import serial.tools.list_ports
import threading
import time

# 내부 모듈 호출
from Utility import log
import Config
from _System_ import SystemState

class HardwareController:
    def __init__(self, state: SystemState):
        self.state = state  # SystemState 인스턴스를 올바르게 저장
        self.ser = None
        self.last_heartbeat_time = time.time()
        self.stop_event = threading.Event()
        self.reconnect_event = threading.Event()

    def _find_serial_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # 아두이노 식별 키워드 (환경에 맞게 추가/수정 가능)
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
                    self.reconnect_event.clear()  # 재연결 성공 시 플래그 초기화
                    self.last_heartbeat_time = time.time()
                    return True
                except serial.SerialException as e:
                    log.warning(f"{port}에 연결을 실패했습니다: {e}")
            else:
                log.warning("연결할 시리얼 포트를 찾지 못하였습니다.")
            
            log.warning(f"{Config.RECONNECT_DELAY}초 후 재연결을 시도합니다.")
            time.sleep(Config.RECONNECT_DELAY) # 수정: 올바른 sleep 호출
        return False
    
    def _read_thread_worker(self):
        while not self.stop_event.is_set():
            if self.reconnect_event.is_set():
                time.sleep(1)
                continue

            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue
                    
                    if line.startswith("SENSOR:"):
                        # SENSOR: {TEMP},{SOIL},{HUMID},{LIGHT} 순서의 데이터 처리
                        items = line[7:].split(',')
                        if len(items) == 4:
                            # 1. 파일에서 현재 최신 상태를 읽어온다 (매우 중요).
                            current_data = self.state.get_all_data()
                            
                            # 2. 읽어온 데이터에서 'SENSOR' 부분만 업데이트한다.
                            current_data["SENSOR"]["TEMP"] = float(items[0])
                            current_data["SENSOR"]["SOIL"] = float(items[1])
                            current_data["SENSOR"]["HUMID"] = float(items[2])
                            current_data["SENSOR"]["LIGHT"] = float(items[3])
                            
                            # 3. 변경된 전체 데이터를 다시 파일에 쓴다.
                            self.state.write_state(current_data)
                            log.debug(f"센서 값 업데이트 완료: {current_data['SENSOR']}")
                        else:
                            log.warning(f"수신한 센서 데이터 형식이 올바르지 않습니다: {line}")

                    elif line.startswith("HEARTBEAT:"):
                        self.last_heartbeat_time = time.time()
                        log.debug("HeartBeat 신호를 수신하였습니다.")

                except (UnicodeDecodeError, ValueError) as e:
                    log.warning(f"시리얼 데이터 파싱 중 오류 발생: {e}")
            
            time.sleep(0.1)

    def _write_thread_worker(self):
            if not self.reconnect_event.is_set() and self.ser and self.ser.is_open:
                try:
                    # 항상 최신 상태를 읽어와서 액추에이터 값을 사용
                    actuator_data = self.state.get_all_data()["ACTUATOR"]
                    
                    # 순서가 보장되는 리스트(List)를 사용하고, .get()으로 안전하게 접근
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
            
            # 제어 주기에 맞춰 대기
            time.sleep(Config.CONTROL_INTERVAL)

    def _watchdog_thread(self):
        while not self.stop_event.is_set():
            if not self.reconnect_event.is_set():
                if time.time() - self.last_heartbeat_time > Config.HEARTBEAT_TIMEOUT:
                    log.warning("지정된 시간 내에 HeartBeat이 수신되지 않았습니다. 재연결을 시작합니다.")
                    self.trigger_reconnect()
            time.sleep(1)

    def trigger_reconnect(self):
        if self.reconnect_event.is_set():
            return  # 이미 재연결 과정이 진행 중이면 중복 실행 방지
        
        log.info("재연결 과정을 시작합니다.")
        self.reconnect_event.set()

        if self.ser:
            try:
                self.ser.close()
            except Exception as e:
                log.error(f"시리얼 포트 종료 중 오류 발생: {e}")
            finally:
                self.ser = None

        # 별도 스레드에서 연결을 재시도하여 메인 로직을 막지 않음
        reconnect_thread = threading.Thread(target=self.connect, daemon=True)
        reconnect_thread.start()

    def start(self):
        log.info("하드웨어 컨트롤러를 시작합니다.")
        
        if not self.connect():
            log.error("초기 연결에 실패하였습니다. 프로그램을 종료합니다.")
            return
        
        # 데몬 스레드로 설정하여 메인 프로그램 종료 시 함께 종료되도록 함
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