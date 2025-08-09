import tkinter as tk
from tkinter import ttk
import requests
import threading

BACKEND_URL = "http://localhost:5000"  # Flask 백엔드 주소

class ControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("스마트 팜 제어 시스템")

        # 센서 데이터 출력용 라벨 프레임
        self.sensor_frame = ttk.LabelFrame(root, text="센서 정보")
        self.sensor_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.sensor_labels = {}
        for i, key in enumerate(["TEMP", "SOIL", "HUMID", "LIGHT"]):
            ttk.Label(self.sensor_frame, text=f"{key}: ").grid(row=i, column=0, sticky="w")
            lbl = ttk.Label(self.sensor_frame, text="0")
            lbl.grid(row=i, column=1, sticky="w")
            self.sensor_labels[key] = lbl

        # FAN, PUMP 슬라이더 제어 프레임
        self.pwm_frame = ttk.LabelFrame(root, text="PWM 제어")
        self.pwm_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.pwm_controls = {}
        for i, device in enumerate(["FAN", "PUMP"]):
            ttk.Label(self.pwm_frame, text=device).grid(row=i, column=0, sticky="w")
            slider = ttk.Scale(self.pwm_frame, from_=0, to=255, orient="horizontal")
            slider.set(0)
            slider.grid(row=i, column=1, padx=5)
            btn = ttk.Button(self.pwm_frame, text="전송", command=lambda d=device, s=slider: self.send_pwm(d, int(s.get())))
            btn.grid(row=i, column=2)
            self.pwm_controls[device] = slider

        # ON/OFF 제어 프레임
        self.toggle_frame = ttk.LabelFrame(root, text="ON/OFF 제어")
        self.toggle_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.toggle_buttons = {}
        for i, device in enumerate(["PNT_LED", "WHITE_LED", "HEAT_PANNEL"]):
            var = tk.StringVar(value="OFF")
            btn = ttk.Checkbutton(self.toggle_frame, text=device, variable=var, onvalue="ON", offvalue="OFF",
                                   command=lambda d=device, v=var: self.send_toggle(d, v.get()))
            btn.grid(row=i, column=0, sticky="w")
            self.toggle_buttons[device] = var

        self.update_status_loop()  # 실시간 상태 갱신 시작

    def update_status_loop(self):
        def fetch():
            try:
                response = requests.get(f"{BACKEND_URL}/status")
                if response.status_code == 200:
                    data = response.json()
                    for key, lbl in self.sensor_labels.items():
                        lbl.config(text=str(data["SENSOR"].get(key, 0)))
            except Exception as e:
                print("상태 요청 실패:", e)

            self.root.after(2000, self.update_status_loop)  # 2초마다 반복

        threading.Thread(target=fetch, daemon=True).start()

    def send_pwm(self, device, value):
        try:
            data = {device: value}
            res = requests.post(f"{BACKEND_URL}/control", json=data)
            print(res.json())
        except Exception as e:
            print(f"{device} 전송 실패:", e)

    def send_toggle(self, device, value):
        try:
            data = {device: value}
            res = requests.post(f"{BACKEND_URL}/control", json=data)
            print(res.json())
        except Exception as e:
            print(f"{device} 제어 실패:", e)


if __name__ == "__main__":
    root = tk.Tk()
    app = ControlPanel(root)
    root.mainloop()
