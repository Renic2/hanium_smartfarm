import serial
import time

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

        except:
            print("파싱 오류 발생") # 예외 처리 (포맷 오류 등)

time.sleep(2) # Loop Delay