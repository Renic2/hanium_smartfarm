# 백엔드에서 라즈베리와 아두이노의 통신을 담당하고 이를 연산하는 파트
# 추가로 로그를 남기고 조건에 따른 동작을 수행하는 기능도 포함
# 2025.07.23 에러코드 추가 밑 시스템 상태 딕셔너리 추가

import time     # PID에서 시간 관련 기능 사용
import os       # 디텍토리 형성 및 로그 경로 설정
import serial   # serial 통신
import serial.tools.list_ports
import logging  # 로그 기록
import threading # 멀티스레딩 구현
from flask import Flask, request # Flask 웹 서버 구현
from datetime import datetime  # 로그 파일명에 현재 시간 사용

# Flask 세팅
app = Flask(__name__)  # Flask 앱 생성

# 전역 변수 지정
sensor_data = {
    "TEMP": 0.0, "SOIL": 0.0, "HUMID": 0.0, "LIGHT": 0.0
} # 센서 데이터 초기화 및 딕셔너리 형태로 저장

control_value = {
    "FAN": 0, "PUMP": 0, # PWM
    "PNT_LED": 0, "WHITE_LED": 0, "HEAT_PANNEL": 0 # ON/OFF
} # 제어 값 초기화 및 딕셔너리로 저장, PWM 제어가 아닌 것들은
  # 0이 OFF, 1이 ON으로 설정

condition_data = {
    "TARGET_TEMP": 25.0, "TARGET_SOIL": 400.0, # 목표 온도 및 토양 습도
}

mannual_override = {} # 사용자 수동 제어 값 저장용 딕셔너리

# 시리얼 통신에 사용되는 변수와 객체
ser = None # 시리얼 포트 객체
is_locked = False # 시리얼 포트 탐색 잠금 상태

# 작동시 발생하는 에러 저장용
system_status = {
    "SERIAL" : {
        "PORT": None, "STATUS": "DISCONNECTED",
        "ERROR_CODE": "0000", "MESSAGE": "포트 탐색 중"
    },

    "SENSOR" : {
        "STATUS": "NORMAL", "ERROR_CODE": "0000",
        "MESSAGE": "정상 작동 중"
    },

    "CONTROL" : {
        "STATUS": "NORMAL", "ERROR_CODE": "0000",
        "MESSAGE": "정상 작동 중"
    },

    "SYSTEM" : {
        "STATUS": "NORMAL", "ERROR_CODE": "0000",
        "MESSAGE": "시스템 정상 작동 중"
    }
}

# 시리얼 포트 탐색 및 연결
def search_serial_port(): # 시리얼 포트 탐색
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.device or 'ACM' in port.device or 'COM'in port.device:
            return port.device
        
    return None

def connect_lock(): # 시리얼 포트 연결 함수, 포트 탐색시 잠김
    global ser, is_locked, system_status
    while not is_locked: # 포트 탐색이 잠기지 않으면 탐색
        port = search_serial_port()

        if port is None: # 포트가 없으면 5초 후 재시도
            system_status["SERIAL"] = {
                "port": port,
                "status": "disconnected",
                "error_code": "0824",
                "message": str("포트 탐색 실패")
            }
            time.sleep(5)
            continue
    
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            # 시리얼 포트 연결 성공
            system_status["SERIAL"] = {
                "port": port,
                "status": "connected",
                "error_code": "0001",
                "message": str("연결 성공")
            }

        except Exception as e: # 연결 실패시 예외 처리
            system_status["SERIAL"] = {
                "port": port,
                "status": "disconnected",
                "error_code": "5637",
                "message": str(e)
            }
        
# 명령어 전송
# 아두이노에서 받는 명령어
# 형식- control_cmd:FAN,PUMP,PNT_LED,WHITE_LED,HEAT_PANNEL
# 실제 출력- control_cmd:255,255,1,0,1
def send_cmd(cmd_str):
    global control_value
    cmd_list = [
        str(control_value["FAN"]),
        str(control_value["PUMP"]),
        str(control_value["PNT_LED"]),
        str(control_value["WHITE_LED"]),
        str(control_value["HEAT_PANNEL"])
    ]

    cmd_str = ','.join(cmd_list)  # 명령어 문자열 생성

    try:
        if ser:
            ser.write((cmd_str + "\n").encode('utf-8'))
    
    except Exception as e:
        system_status["CONTROL"] = {
            "STATUS": "ERROR",
            "ERROR_CODE": "0070",
            "MESSAGE": str(e)
        }

# 센서 데이터 읽기
# 받는 포맷 - sensor:(TEMP),(SOIL),(HUMID),(LIGHT)
# 예시 포맷 - sensor:25.5,300,45,1000
def get_sensor_data():
    global ser, sensor_data, system_status
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line.startswith("sensor:"):
                    line = line[7:] # sensor: 접두사 제거
                    items = line.split(',') # 센서값 분리

                if len(items) == 4: # 4개의 센서값이 있어야 함
                    sensor_data["TEMP"] = float(items[0])
                    sensor_data["SOIL"] = float(items[1])
                    sensor_data["HUMID"] = float(items[2])
                    sensor_data["LIGHT"] = float(items[3])
                
            except Exception as e:
                system_status["SENSOR"] = {
                    "STATUS": "ERROR",
                    "ERROR_CODE": "1234",
                    "MESSAGE": str(e)
                }

        time.sleep(2)  # 2초 간격으로 센서 데이터 읽기

# PID 제어 클래스
class PID: 
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

# 자동 제어 함수
def auto_control():
    pid = PID(Kp=5.0, Ki=0.1, Kd=10.0, 
              setpoint=float(condition_data["TARGET_TEMP"]))
    
    while True:
        try:
            if "FAN" not in mannual_override:
                output = pid.compute(sensor_data["TEMP"])
            pwm_value = int(max(min((output + 10) * 12.75, 255),0))
            control_value["FAN"] = pwm_value

            if output > 1:
                control_value["HEAT_PANNEL"] = 0
            elif output < -1:
                control_value["HEAT_PANNEL"] = 1
            else:
                control_value["HEAT_PANNEL"] = 0

            if "PUMP" not in mannual_override:
                if sensor_data["SOIL"] < condition_data["TARGET_SOIL"]:
                    control_value["PUMP"] = 200
                    send_cmd()
                    time.sleep(2)
                    control_value["PUMP"] = 0
            
            send_cmd()
            time.sleep(2)  # 2초 간격으로 제어

        except Exception as e:
            system_status["CONTROL"] = {
                "STATUS": "ERROR",
                "ERROR_CODE": "0122",
                "MESSAGE": str(e)
            }
            time.sleep(2)

# FLASK API

@app.route('/status', methods=['GET'])
def get_status():
    