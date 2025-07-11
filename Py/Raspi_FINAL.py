# 구현해야 하는 것 : 센서값 받기 Clear
#                  명령 입력 (SERIAL 명령) 
#                  시리얼 포트 자동 탐색 (내가 귀찮음) Clear
#                  PID 제어로 입력받은 온도값 유지  Clear
#                  멀티스레딩으로 구현

import serial
import serial.tools.list_ports # 자동 포트 찾기
import time
import threading # threading 모듈을 사용하여 멀티스레딩 구현

from serial.tools import list_ports

# 전역 변수
sensor_data = {
    "TEMP": 0,
    "SOIL": 0,
    "HUMID": 0,
    "LIGHT": 0
}

condition_data = {
    "MIN_SOIL": 100, # 최대 토양 습도
    "MIN_HUMID": 30, # 최소 습도
    "MAX_HUMID": 70, # 최대 습도
    "MIN_LIGHT": 100, # 최소 조도
    "MAX_LIGHT": 800, # 최대 조도
    "TARGET_TEMP": 25 # 목표 온도
}

ser = None
is_locked = False # 포트 탐색 루프 잠금 여부

mannual_override = {} # 수동 모드 여부

def search_serial_port(): # 시리얼 포트 탐색
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.device or 'ACM' in port.device:
            return port.device
        
    return None

def connect_lock(): # 연결 시도
    global ser, is_locked

    while not is_locked:
        port = search_serial_port()
        
        if port is None:
            print("포트 탐색 실패, 5초 후 재시도합니다.")
            time.sleep(5)
            continue

        try:
            ser = serial.Serial(port, 9600, timeout=1)
            print(f"연결 성공 : {port}")
            is_locked = True # connect_lock을 LOCK 시킴

        except Exception as e:
            print(f"연결 실패 : {e}")
            print("5초 후 재시도합니다.")
            time.sleep(5)

def get_sensor_data(): # 센서 데이터 읽기 (Thread 1)
    global ser, sensor_data

    while True:
        if ser and ser.in_waiting: # 데이터 도착시에만 처리
            try:
                line = ser.readline().decode('utf-8').strip()
                
                data = dict(item.split(':') for item in line.split(','))

                parsed = {
                    "SOIL": int(data.get('SOIL', 0)), # Soil Humid
                    "TEMP": int(data.get('TEMP', 0)), # Temp
                    "HUMID": int(data.get('HUM', 0)), # Humid
                    "LIGHT": int(data.get('LIGHT', 0)) # Light
                }
                sensor_data.update(parsed) # 센서 데이터 업데이트

                print(f"[Sensor]: {sensor_data}")

            except Exception as e:
                print(f"[파싱 에러] 무시됨 : {e}")

        time.sleep(2)

def send_command(cmd_str): # 아두이노로 명령 전송
    global ser
    
    try:
        ser.write((cmd_str + "\n").encode('utf-8'))
        print(f"[명령 전송] {cmd_str}")
    
    except Exception as e:
        print(f"[명령 전송 실패] : {e}")

def auto_control(): # 자동 제어 로직 (Thread 2)
    global sensor_data, mannual_override

    pid = PID(Kp=1.0, Ki=0.1, Kd=0.05, setpoint=int(condition_data["TARGET_TEMP"]))

    while True:
        current_temp = sensor_data["TEMP"]
        output = pid.compute(current_temp)

        # manual ovverride가 활성화된 경우 PID 제어를 무시
        if "FAN" in mannual_override or "HEAT_PANNEL" in mannual_override:
            time.sleep(2)
            continue

        if output > 1.0:
            send_command("FAN: ON")
            send_command("HEAT_PANNEL: OFF")
        elif output < -1.0:
            send_command("FAN: OFF")
            send_command("HEAT_PANNEL: ON")
        else:
            send_command("FAN: OFF")
            send_command("HEAT_PANNEL: OFF")

        time.sleep(3)

def user_input(): # 사용자 입력 처리 (Thread 3)
    global mannual_override

    while True:
        cmd = input("[COMMAND] 명령어 입력: ")
        if cmd.upper() == "RESET":
            mannual_override.clear()
            print("[MODE] 수동 제어 모드 해제")

        else:
            try:
                device, status = cmd.upper().split()
                mannual_override[device] = status
                send_command(f"{device}:{status}")
            
            except Exception as e:
                print(f"[FORMAT ERROR] '장치 상태' 형식으로 입력 - {e}")

class PID: # PID 제어
    def __init__(self, Kp, Ki, Kd, setpoint=0):
        self.Kp = Kp # 비례 게인
        self.Ki = Ki # 적분 게인
        self.Kd = Kd # 미분 게인

        self.setpoint = setpoint # 목표값
        self.last_error = 0
        self.integral = 0
        self.last_time = None

    def compute(self, measured_value):
        current_time = time.time()
        error = self.setpoint - measured_value

        dt = 0
        if self.last_time is not None:
            dt = current_time - self.last_time

        self.integral += error * dt if dt > 0 else 0

        derivative = (error - self.last_error) / dt  if dt > 0 else 0

        # PID OUTPUT
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

        self.last_error = error 
        self.last_time = current_time

        output = max(min(output, 10.0), -10.0)  # 제한: -1.0 ~ 1.0 범위

        return output

if __name__ == "__main__":
    connect_lock()  # 포트 연결 루프, 연결 시 LOCK

    threading.Thread(target=get_sensor_data, daemon=True).start()  # 센서 데이터 읽기 스레드
    threading.Thread(target=auto_control, daemon=True).start()  # 자동 제어 스레드
    threading.Thread(target=user_input, daemon=True).start()  # 사용자 입력 스레드

    while True:
        time.sleep(1)
        # 메인 루프는 스레드가 계속 실행되도록 유지