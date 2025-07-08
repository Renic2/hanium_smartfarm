import serial
import time

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

            command = input()

            if command == "PUMP":
                send_command("PUMP: ON")
                time.sleep(10)
                send_command("PUMP: OFF")

            if command == "FAN_ON":
                send_command("FAN: ON")
                time.sleep(10)
                send_command("FAN: OFF")

            if command == "FAN_OFF":
                send_command("FAN: OFF")
                             
            if command == "HEAT_PANNEL_ON":
                send_command("HEAT_PANNEL: ON")

            if command == "HEAT_PANNEL_OFF":
               send_command("HEAT_PANNEL: OFF")
        

        except:
            print("파싱 오류 발생") # 예외 처리 (포맷 오류 등)

time.sleep(2) # Loop Delay