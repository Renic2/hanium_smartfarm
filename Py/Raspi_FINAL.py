import serial
import time

# PORT and Speed Setting
ser = serial.Serial('COM4', 9600, timeout=1)
time.sleep(2) # Waiting for Connection

def send_command(cmd_str):
    ser.write((cmd_str + "\n").encode('utf-8'))

class PID:
    def __init__(self, Kp, Ki, Kd, setpoint=0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.last_error = 0
        self.integral = 0
        self.last_time = None

    def compute(self, measured_value):
        current_time = time.time()
        error = self.setpoint - measured_value
        dt = current_time - self.last_time if self.last_time else 0.01
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        self.last_error = error
        self.last_time = current_time
        return (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)

temp_pid = PID(1.2, 0.05, 0.2, setpoint=25.0)

while True:
    if ser.in_waiting: # IF RECEIVED DATA EXIST
        line = ser.readline().decode('utf-8').strip()

    print(f"Senserdata:", line)
    try:
        data = dict(item.split(':') for item in line.split(','))
        temp = float(data.get("TEMP", 0))

        output = temp_pid.compute(temp)

        if output > 1.0:
            send_command("HEAT_PANNEL: ON")
            send_command("FAN: OFF")
        elif output < -1.0:
            send_command("HEAT_PANNEL: OFF")
            send_command("FAN: ON")
        else:
            send_command("HEAT_PANNEL: OFF")
            send_command("FAN: OFF")

    except Exception as e:
        print("에러:", e)

    time.sleep(2)