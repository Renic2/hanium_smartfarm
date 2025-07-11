# 구현해야 하는 것 : 센서값 받기 Clear
#                  명령 입력 (SERIAL 명령) 
#                  시리얼 포트 자동 탐색 (내가 귀찮음) Clear
#                  PID 제어로 입력받은 온도값 유지  Clear
#                  멀티스레딩으로 구현

import serial
import serial.tools.list_ports
import time
import threading

# 전역 변수
sensor_data = {
    "TEMP": 0.0,
    "SOIL": 0.0,
    "HUMID": 0.0,
    "LIGHT": 0.0
}

condition_data = {
    "MIN_SOIL": 100,    # 최소 토양 습도
    "MIN_HUMID": 30,    # 최소 습도
    "MAX_HUMID": 70,    # 최대 습도
    "MIN_LIGHT": 100,   # 최소 조도
    "MAX_LIGHT": 800,   # 최대 조도
    "TARGET_TEMP": 25   # 목표 온도
}

ser = None
is_locked = False
mannual_override = {}
is_input_mode = False  # 사용자 입력 중인지 여부
print_lock = threading.Lock()  # 출력 동기화

def thread_safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

def search_serial_port():
    for port in serial.tools.list_ports.comports():
        if 'USB' in port.device or 'ACM' in port.device:
            return port.device
    return None

def connect_lock():
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

def get_sensor_data():
    global ser, sensor_data
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8').strip()
                data = dict(item.split(':') for item in line.split(','))

                parsed = {
                    "SOIL": float(data.get('SOIL', 0)),
                    "TEMP": float(data.get('TEMP', 0)),
                    "HUMID": float(data.get('HUM', 0)),
                    "LIGHT": float(data.get('LIGHT', 0))
                }

                sensor_data.update(parsed)

                if not is_input_mode:
                    thread_safe_print(f"[Sensor]: {sensor_data}")

            except Exception as e:
                if not is_input_mode:
                    thread_safe_print(f"[파싱 에러] 무시됨 : {e}")
        time.sleep(2)

def send_command(cmd_str):
    global ser
    try:
        ser.write((cmd_str + "\n").encode('utf-8'))
        thread_safe_print(f"[명령 전송] {cmd_str}")
    except Exception as e:
        thread_safe_print(f"[명령 전송 실패] : {e}")

def auto_control():
    global sensor_data, mannual_override
    pid = PID(Kp=5.0, Ki=0.1, Kd=10.0, setpoint=float(condition_data["TARGET_TEMP"]))
    while True:
        current_temp = sensor_data["TEMP"]
        output = pid.compute(current_temp)

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

def user_input():
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

if __name__ == "__main__":
    connect_lock()

    threading.Thread(target=get_sensor_data, daemon=True).start()
    threading.Thread(target=auto_control, daemon=True).start()
    threading.Thread(target=user_input, daemon=True).start()

    while True:
        time.sleep(1)
