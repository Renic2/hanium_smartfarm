import serial
import time

# PORT and Speed Setting
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)

while True:
    if ser.in_waiting:
        line = ser.readline().decode('utf-8').rstrip()
        print(f"Received: {line}")