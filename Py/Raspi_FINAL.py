# 구현해야 하는 것
#   센서값 받기 Clear
#   명령 입력 (SERIAL 명령) 
#   시리얼 포트 자동 탐색 (내가 귀찮음) Clear
#   PID 제어로 입력받은 온도값 유지  Clear
#   멀티스레딩으로 구현
#   조건 구현 - PID(FAN, HEAT_PANNEL) Clear, 토양습도
#   토양 습도 -> PUMP, 온도 -> FAN, HEAT_PANNEL, 사진 촬영 or 사용자 설정 -> White LED

import serial
import serial.tools.list_ports
import time
import threading
import os
import logging
from datetime import datetime

# 전역 변수
sensor_data = {
    "TEMP": 0.0, "SOIL": 0.0, "HUMID": 0.0, "LIGHT": 0.0
}

condition_data = {
    "MIN_SOIL": 100, "MIN_HUMID": 30,
    "MAX_HUMID": 70, "MIN_LIGHT": 100,
    "MAX_LIGHT": 800, "TARGET_TEMP": 25,
    "TARGET_SOIL" : 400 
}

ser = None
is_locked = False
mannual_override = {}
is_input_mode = False  # 사용자 입력 중인지 여부
print_lock = threading.Lock()  # 출력 동기화
data_lock = threading.Lock()  # 데이터 동기화

# 로그 디텍토리 생성

log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 로그 파일명 (ex: logs/2025-06-28_23:50:23.log)
log_filename = datetime.now().strftime("log/%Y-%m-%d.log")
log_path = os.path.join(log_dir, log_filename)

# Logging 모듈 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] - %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def thread_safe_print(*args, **kwargs): # 출력 함수 잠금
    with print_lock:
        print(*args, **kwargs)

def search_serial_port(): # 시리얼 포트 탐색
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.device or 'ACM' in port.device:
            return port.device
    return None

def connect_lock(): # 시리얼 포트 연결 함수
    global ser, is_locked
    while not is_locked:
        port = search_serial_port()
        if port is None:
            thread_safe_print("포트 탐색 실패, 5초 후 재시도합니다.")
            time.sleep(5)
            continue
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            thread_safe_print(f"연결 성공 : {port}")
            is_locked = True
        except Exception as e:
            thread_safe_print(f"연결 실패 : {e}")
            thread_safe_print("5초 후 재시도합니다.")
            time.sleep(5)

def get_sensor_data(): # 센서 데이터 읽기
    global ser, sensor_data
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                items = line.split(',')
                parsed = {}

                for item in items:
                    if ':' in item:
                        key, value = item.split(':', 1)
                        parsed[key.strip().upper()] = float(value.strip())

                with data_lock:
                    sensor_data.update({
                        "TEMP": parsed.get("TEMP", sensor_data["TEMP"]),
                        "SOIL": parsed.get("SOIL", sensor_data["SOIL"]),
                        "HUMID": parsed.get("HUMID", sensor_data["HUMID"]),
                        "LIGHT": parsed.get("LIGHT", sensor_data["LIGHT"])
                    })

                if not is_input_mode:
                    thread_safe_print(f"[Sensor]: {sensor_data}")

            except Exception as e:
                if not is_input_mode:
                    thread_safe_print(f"[ERROR] 무시됨 : {e}")
        time.sleep(2)

def send_command(cmd_str): # 명령어 전송 함수
    global ser

    try:
        ser.write((cmd_str + "\n").encode('utf-8'))
        thread_safe_print(f"[전송] {cmd_str}")

    except Exception as e:
        thread_safe_print(f"[전송 실패] : {e}")

def auto_control(): # 자동 제어 함수
    global sensor_data, mannual_override
    pid = PID(Kp=5.0, Ki=0.1, Kd=10.0, setpoint=float(condition_data["TARGET_TEMP"]))
    while True:
        current_temp = sensor_data["TEMP"]
        current_soil = sensor_data["SOIL"]

        if any(k in mannual_override for k in ["FAN", "HEAT_PANNEL"]):
            time.sleep(2)
            continue

        output = pid.compute(current_temp)

        if output > 1.0:
            send_command("FAN: ON")
            send_command("HEAT_PANNEL: OFF")
        elif output < -1.0:
            send_command("FAN: OFF")
            send_command("HEAT_PANNEL: ON")
        else:
            send_command("FAN: OFF")
            send_command("HEAT_PANNEL: OFF")

        if current_soil < condition_data["TARGET_SOIL"]:
            send_command("PUMP: ON")
            time.sleep(3)  # 물 주는 시간
            send_command("PUMP: OFF")

        time.sleep(3)

def user_input(): # 사용자 입력 함수
    global mannual_override, is_input_mode

    while True:
        try:
            is_input_mode = True
            cmd = input("[COMMAND] 명령어 입력: ").strip()
        finally:
            is_input_mode = False

        if cmd.upper() == "RESET":
            mannual_override.clear()
            thread_safe_print("[MODE] 수동 제어 모드 해제")
        else:
            try:
                device, status = cmd.upper().split()
                mannual_override[device] = status
                send_command(f"{device}:{status}")

            except Exception as e:
                thread_safe_print(f"[FORMAT ERROR] '장치 상태' 형식으로 입력 - {e}")

class PID: # PID 제어 클래스
    def __init__(self, Kp, Ki, Kd, setpoint=0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = float(setpoint)
        self.last_error = 0.0
        self.integral = 0.0
        self.last_time = None

    def compute(self, measured_value):
        current_time = time.time()
        error = self.setpoint - measured_value

        dt = 0.0
        if self.last_time is not None:
            dt = current_time - self.last_time

        self.integral += error * dt if dt > 0 else 0.0
        derivative = (error - self.last_error) / dt if dt > 0 else 0.0

        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        self.last_error = error
        self.last_time = current_time

        output = max(min(output, 10.0), -10.0)  # 출력 제한

        return output

if __name__ == "__main__":
    connect_lock()

    threading.Thread(target=get_sensor_data, daemon=True).start()
    threading.Thread(target=auto_control, daemon=True).start()
    threading.Thread(target=user_input, daemon=True).start()

    while True:
        time.sleep(1)
