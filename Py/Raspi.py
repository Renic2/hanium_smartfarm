import serial
import time

Max_Temp = 22.0 # Temp 상한선
Min_Temp = 15.0 # Temp 하한선 
Max_Soil = 600 # 토양습도 상한 (혹시 모르기에 값을 좀 줄여놈)
Min_Soil = 30 # 토양습도 하한

# PORT and Speed Setting
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2) # Waiting for Connetion

def send_command(cmd_str): # Sending to Arduino
    ser.write((cmd_str + "\n").encode('utf-8'))

while True: # Main loop
    if ser.in_waiting: # If Received data is exist
        line = ser.readline().decode('utf-8').strip()
        # 한 줄 읽고 디코딩
        print(f"Senserdata:", line)

        try:
            data = dict(item.split(':') for item in line.split(','))
            # 문자열 -> Dict
            soil = int(data.get('SOIL', 0)) # Soil Humid
            temp = int(data.get('TEMP', 0)) # Temp
            humid = int(data.get('HUM', 0)) # Humid
            light = int(data.get('LIGHT', 0)) # Light 

            if soil > Max_Soil: #PUMP CONTROL
                send_command("PUMP: OFF")
            elif soil < Min_Soil:
                send_command("PUMP: ON")

            if temp > Max_Temp:
                send_command("FAN: ON")
            elif temp < Max_Temp -2:
                send_command("FAN: OFF")
            elif temp < Min_Temp:
                send_command("HEAT_PANNEL: ON")
            elif temp > Min_Soil +2:
                send_command("HEAT PANNEL: OFF")

        except:
            print("파싱 오류 발생") # 예외 처리 (포맷 오류 등)

    

time.sleep(2) # Loop Delay

class PID:
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