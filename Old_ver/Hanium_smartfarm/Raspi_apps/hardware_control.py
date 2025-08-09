# -----------------------------------------------------------------------
# hardware_control.py
# 아두이노와의 시리얼 통신, 센서/액추에이터 제어 송수신
# 하드웨어 관련 전담
# Heartbeat & Watchdog를 통한 안정적인 유지 목표
# -----------------------------------------------------------------------

import serial
import serial.tools.list_ports
import threading
import time
import json
from util import log
import config
from system_state import SystemState

class HardwareController:
    def __init__(self, state: SystemState):
        self.state = state
        self.ser = None
        self.last_heartbeat_time = time.time()

        # 스레드를 안전하게 종료하기 위한 이벤트 객체
        self.stop_event = threading.Event()
        self.reconnect_event = threading.Event()

    def _find_serial_port(self):
        # 시리얼 포트 자동 탐색
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # 아두이노로 추정되는 장치의 키워드
            if 'USB' in port.device or 'ACM' in port.device or 'COM' in port.device:
                return port.device
        return None
    
    def connect(self):
        # 시리얼 포트에 연결 시도, 실패 시 재시도
        while not self.stop_event.is_set():
            port = config.SERIAL_PORT or self._find_serial_port()
            if port:
                try:
                    self.ser = serial.Serial(port, config.BAUD_RATE, timeout=1)
                    log.info(f"Arduino connected successfully on port {port}.")
                    self.reconnect_event.clear() # 재연결 성공 시 이벤트 초기화
                    self.last_heartbeat_time = time.time()
                    return True # 연결 성공
                
                except serial.SerialException as e:
                    log.warning(f"Failed to connect to {port}: {e}. Retrying in 5 seconds...")
            
            else:
                log.warning("No serial port found. Retrying in 5 seconds...")
            
            time.sleep(5)
        return False
    
    def _read_thread_worker(self):
        # 시리얼 포트로부터 지속적으로 데이터를 읽는 스레드 워커
        while not self.stop_event.is_set():
            if self.reconnect_event.is_set():
                time.sleep(1)
                continue

            if self.ser and self.ser.in_waiting:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    
                    # Heartbeat 메시지 처리
                    if data.get("TYPE") == "HEARTBEAT":
                        self.last_heartbeat_time = time.time()
                        log.debug("Heartbeat received from Arduino.")
                    
                    # 센서 데이터 처리
                    else:
                        log.info(f"[RECV] {line}")
                        self.state.update_sensors(data)

                except json.JSONDecodeError:
                    log.warning(f"Received invalid JSON from Arduino: {line}")
                
                except (UnicodeDecodeError, serial.SerialException) as e:
                    log.error(f"Serial read error: {e}")
                    self.trigger_reconnect()
            time.sleep(0.1)

    def _watchdog_thread_worker(self):
        # Heartbeat를 확인하여 연결 상태를 확인하는 Watchdog 스레드 워커
        while not self.stop_event.is_set():
            if not self.reconnect_event.is_set():
                if time.time() - self.last_heartbeat_time > config.HEARTBEAT_TIMEOUT:
                    log.warning("Heartbeat timeout! Connection lost.")
                    self.trigger_reconnect()
            time.sleep(1)

    def trigger_reconnect(self):
        # 재연결 시도
        if self.reconnect_event.is_set():
            return
        
        log.info("Triggering reconnection procedure...")
        self.reconnect_event.set()
        if self.ser:
            try:
                self.ser.close()

            except Exception as e:
                log.error(f"Error closing serial port: {e}")
            
            finally:
                self.ser = None

        # 별도 스레드에서 연결 재시도
        reconnect_thread = threading.Thread(target=self.connect, daemon=True)
        reconnect_thread.start()

    def send_command(self, device: str, value: int):
        # 아두이노 제어 명령 (JSON 형태) 전송
        if self.ser and self.ser.is_open:
            try:
                command = {"DEVICE": device.upper(), "VALUE": int(value)}
                json_command = json.dumps(command) + '\n'
                self.ser.write(json_command.encode('utf-8'))
                log.info(f"[SEND] {json_command.strip()}")
                # 명령 전송 후, 시스템 상태에도 반영
                self.state.update_actuator_state(device, value)
            
            except (serial.SerialException, TypeError) as e:
                log.error(f"Failed to send command: {e}")
                self.trigger_reconnect()
        
        else:
            log.warning("Cannot send command. Serial port is not connected.")

    def start(self):
        # 모든 제어 스레드 시작
        log.info("Starting hardware communication threads...")
        
        # 초기 연결
        if not self.connect():
            # 초기 연결 실패 시 조치
            log.error("Initial connection failed. Please check the hardware.")
            return
        
        # 스레드 시작
        threading.Thread(target=self._read_thread_worker, daemon=True).start()
        threading.Thread(target=self._watchdog_thread_worker, daemon=True).start()
        log.info("Hardware controller is running.")

    def stop(self):
        # 스레드 정료 후 시리얼 포트 닫기
        log.info("Stopping hardware controller...")
        self.stop_event.set()
        if self.ser and self.ser.is_open:
            self.ser.close()
        log.info("Hardware controller stopped.")