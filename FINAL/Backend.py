import time
import os
import serial
import serial.tools.list_ports
import logging
import threading
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ===== 전역 변수 =====
sensor_data = {
    "TEMP": 0.0, "SOIL": 0.0, "HUMID": 0.0, "LIGHT": 0.0
}

control_value = {
    "FAN": 0, "PUMP": 0,
    "PNT_LED": 0, "WHITE_LED": 0, "HEAT_PANNEL": 0
}

condition_data = {
    "TARGET_TEMP": 25.0, "TARGET_SOIL": 400.0
}

mannual_override = {}

ser = None
is_locked = False

system_status = {
    "SERIAL": {"PORT": None, "STATUS": "DISCONNECTED", "ERROR_CODE": "0000", "MESSAGE": "포트 탐색 중"},
    "SENSOR": {"STATUS": "NORMAL", "ERROR_CODE": "0000", "MESSAGE": "정상 작동 중"},
    "CONTROL": {"STATUS": "NORMAL", "ERROR_CODE": "0000", "MESSAGE": "정상 작동 중"},
    "SYSTEM": {"STATUS": "NORMAL", "ERROR_CODE": "0000", "MESSAGE": "시스템 정상 작동 중"}
}

# ===== 시리얼 연결 =====
def search_serial_port():
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.device or 'ACM' in port.device or 'COM' in port.device:
            return port.device
    return None

def connect_lock():
    global ser, is_locked, system_status
    while not is_locked:
        port = search_serial_port()
        if port is None:
            system_status["SERIAL"] = {
                "PORT": None, "STATUS": "DISCONNECTED",
                "ERROR_CODE": "0824", "MESSAGE": "포트 탐색 실패"
            }
            time.sleep(5)
            continue
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            system_status["SERIAL"] = {
                "PORT": port, "STATUS": "CONNECTED",
                "ERROR_CODE": "0001", "MESSAGE": "연결 성공"
            }
            return
        except Exception as e:
            system_status["SERIAL"] = {
                "PORT": port, "STATUS": "DISCONNECTED",
                "ERROR_CODE": "5637", "MESSAGE": str(e)
            }

# ===== 명령어 전송 =====
def send_cmd():
    try:
        cmd_list = [
            str(control_value["FAN"]),
            str(control_value["PUMP"]),
            str(control_value["PNT_LED"]),
            str(control_value["WHITE_LED"]),
            str(control_value["HEAT_PANNEL"])
        ]
        cmd_str = ','.join(cmd_list)
        if ser:
            ser.write((cmd_str + "\n").encode('utf-8'))
    except Exception as e:
        system_status["CONTROL"] = {
            "STATUS": "ERROR", "ERROR_CODE": "0070", "MESSAGE": str(e)
        }

# ===== 센서 데이터 수신 =====
def get_sensor_data():
    global ser
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                if line.startswith("sensor:"):
                    items = line[7:].split(',')
                    if len(items) == 4:
                        sensor_data["TEMP"] = float(items[0])
                        sensor_data["SOIL"] = float(items[1])
                        sensor_data["HUMID"] = float(items[2])
                        sensor_data["LIGHT"] = float(items[3])
            except Exception as e:
                system_status["SENSOR"] = {
                    "STATUS": "ERROR", "ERROR_CODE": "1234", "MESSAGE": str(e)
                }
        time.sleep(2)

# ===== PID 제어 =====
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
        dt = current_time - self.last_time if self.last_time else 0.0

        self.integral += error * dt if dt > 0 else 0.0
        derivative = (error - self.last_error) / dt if dt > 0 else 0.0

        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.last_error = error
        self.last_time = current_time
        return max(min(output, 10.0), -10.0)

# ===== 자동 제어 =====
def auto_control():
    pid = PID(Kp=5.0, Ki=0.1, Kd=10.0, setpoint=condition_data["TARGET_TEMP"])
    while True:
        try:
            if "FAN" not in mannual_override:
                output = pid.compute(sensor_data["TEMP"])
                pwm_value = int(max(min((output + 10) * 12.75, 255), 0))
                control_value["FAN"] = pwm_value
                control_value["HEAT_PANNEL"] = 1 if output < -1 else 0

            if "PUMP" not in mannual_override:
                if sensor_data["SOIL"] < condition_data["TARGET_SOIL"]:
                    control_value["PUMP"] = 200
                    send_cmd()
                    time.sleep(2)
                    control_value["PUMP"] = 0

            send_cmd()
        except Exception as e:
            system_status["CONTROL"] = {
                "STATUS": "ERROR", "ERROR_CODE": "0122", "MESSAGE": str(e)
            }
        time.sleep(2)

# ===== API =====
@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({
        "SENSOR": sensor_data,
        "CONTROL": control_value,
        "SYSTEM": system_status,
        "TARGET": condition_data,
        "MANUAL_OVERRIDE": mannual_override
    })

@app.route('/control', methods=['POST'])
def manual_control():
    data = request.json
    for device, value in data.items():
        mannual_override[device] = value
        if device in ["FAN", "PUMP"]:
            control_value[device] = int(value)
        else:
            control_value[device] = 1 if value == "ON" else 0
    send_cmd()
    return jsonify({"MESSAGE": "수동 제어 실행", "MANUAL_OVERRIDE": mannual_override})

@app.route('/control/reset', methods=['POST'])
def reset_control():
    mannual_override.clear()
    return jsonify({"MESSAGE": "수동 제어 모드 해제"})

@app.route('/set_target', methods=['POST'])
def set_target():
    data = request.json
    if "TEMP" in data:
        condition_data["TARGET_TEMP"] = float(data["TEMP"])
    if "SOIL" in data:
        condition_data["TARGET_SOIL"] = float(data["SOIL"])
    return jsonify({"MESSAGE": "목표 값 설정 완료", "TARGET": condition_data})

# ===== 실행 시작 =====
if __name__ == "__main__":
    connect_lock()
    threading.Thread(target=get_sensor_data, daemon=True).start()
    threading.Thread(target=auto_control, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
