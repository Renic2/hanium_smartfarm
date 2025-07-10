# 구현해야 하는 것 : 센서값 받기 Clear
#                  명령 입력 (SERIAL 명령) 
#                  시리얼 포트 자동 탐색 (내가 귀찮음) Clear
#                  PID 제어로 입력받은 온도값 유지  Clear

import serial
import serial.tools.list_ports # 자동 포트 찾기
import time

from serial.tools import list_ports

ser = None
is_locked = False # 포트 탐색 루프 잠금 여부

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

def sensor_loop():
    global ser

    while True:
        if ser and ser.in_waiting: # 데이터 도착시에만 처리
            try:
                line = ser.readline().decode('utf-8').strip()
                print(f"Sensor DATA: {line}")
            
            except Exception as e:
                print(f"파싱 에러: {e}")

        time.sleep(0.1)

class PID: # PID 제어
    def __init__(self, Kp, Ki, Kd, setpoint=0):
        self.Kp = Kp # 비례 게인
        self.Ki = Ki # 적분 게인
        self.Kd = Kd # 미분 게인

        self.setpoint = setpoint # 목표값
        self.last_error = 0
        self.integral = 0
        self.lasttime = None

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

        return output

if __name__ == "__main__":
    connect_lock()  # 포트 연결 루프, 연결 시 LOCK
    sensor_loop()   # 데이터 처리 루프