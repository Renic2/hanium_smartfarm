# -----------------------------------------------------------------------
# system_state.py
# 시스템의 실시간 상태와 동적 설정을 관리하는 중앙 저장소
# 여러 스레드에서 안전한 접근을 위한 LOCK 사용
# -----------------------------------------------------------------------

import threading
import json
import os
from datetime import datetime
import config
from util import log

class SystemState:
    # 시스템의 현재 상태와 설정을 관리하는 스레드-안전 클래스

    def __init__(self):
        self.lock = threading.Lock()

        # 센서값 초기화
        self.sensors = {"TEMP": 0.0, "HUMID": 0.0,
                        "SOIL": 0.0, "LIGHT": 0.0}
        
        # FAN, PUMP는 PWM 제어 (0 ~ 255)
        self.actuators = {"FAN": 0, "PUMP": 0,
                          "GROW_LIGHT": 1,
                          "WHITE_LED": 0,
                          "HEAT_PANNEL": 0}
        
        # 동적 목표값 (config.py에서 로드)
        self.targets = {
            "TARGET_TEMP": config.TARGET_TEMP,
            "TARGET_SOIL_MOISTURE":
            config.TARGET_SOIL_MOISTURE
        }

        # 시스템 운영 모드 및 상태
        self.mode = "AUTO" # AUTO or MANUAL
        self.plant_condition = "NORMAL"
        self.last_updated = None

        # 프로그램 시작시 목표값 로딩
        self.load_targets_from_file()

    def update_sensors(self, sensor_data: dict):
        # 센서 데이터 업데이트
        with self.lock:
            self.sensors.update(sensor_data)
            self.last_updated = datetime.now()

    def update_actuator_state(self, device: str, value: int):
        with self.lock:
            device = device.upper()
            if device in self.actuators:
                # 값의 유효성 검사
                try:
                    value_int = int(value)
                    # 값이 int인지 확인
                    clamped_value = max(0, min(255,value_int))
                    # 값이 0 ~ 255 사이인지 확인

                    if self.actuators[device] != clamped_value:
                        self.actuators[device] = clamped_value
                        log.info(f"[STATE] Actuator '{device}' state changed to '{clamped_value}'")
                    
                except (ValueError, TypeError):
                    log.warning(f"Invalid value type for actuator '{device}' Must be an integer. Value:{value}")
            
            else:
                log.warning(f"Attempted to update unknown actuator: {device}")
    
    def update_targets(self, new_targets: dict):
    # 프론트엔드에서 받은 새 목표값 및 모드 업데이트, 저장
        with self.lock:
        # 플래그를 두어 파일 저장은 목표값이 변경될 때만 수행
            targets_changed = False
            for key, value in new_targets.items():
            # 1. 'mode' 키가 들어온 경우, self.mode를 직접 변경
                if key == "mode":
                    if value in ["AUTO", "MANUAL"]:
                        self.mode = value
                        log.info(f"System mode changed to: {self.mode}")
                    else:
                        log.warning(f"Invalid mode value received: {value}")
            
            # 2. 기존 목표값(온도, 습도 등) 키가 들어온 경우, self.targets를 변경
                elif key in self.targets:
                    try:
                    # float[value] -> float(value) 오타 수정
                        self.targets[key] = float(value)
                        targets_changed = True # 목표값이 변경되었음을 표시
                
                    except (ValueError, TypeError):
                        log.warning(f"Invalid value for target '{key}'. Must be a number. Value: {value}")
        
        # 목표값이 실제로 변경되었을 때만 파일에 저장
            if targets_changed:
                log.info(f"Targets updated: {self.targets}")
                self.save_targets_to_file()

    def get_full_state(self) -> dict:
        # 시스템의 현재 상태를 안전하게 복사하여 반환.
        with self.lock:
            return {
                "sensors": self.sensors.copy(),
                "actuators": self.actuators.copy(),
                "targets": self.targets.copy(),
                "mode": self.mode,
                "plant_condition": self.plant_condition,
                "last_updated": self.last_updated.isoformat() if self.last_updated else None
            }
    
    def save_targets_to_file(self):
        # 현재 목표값을 'setpoints.json' 파일에 저장
        try:
            with open("setpoints.json", "w", encoding="utf-8") as f:
                json.dump(self.targets, f, ensure_ascii=False, indent=4)
            log.info("Successfully saved setpoints to setpoints.json")

        except Exception as e:
            log.error(f"Failed to save setpoints to file: {e}")

    def load_targets_from_file(self):
        # 'setpoints.json' 파일에서 목표값을 불러와 적용
        if os.path.exists("setpoints.json"):
            try:
                with open("setpoints.json", "r", encoding="utf-8") as f:
                    loaded_targets = json.load(f)
                    # 파일에서 불러온 값으로 self.targets 업데이트
                    for key, value in loaded_targets.items():
                        if key in self.targets:
                            self.targets[key] = float(value)

                log.info(f"Successfully loaded setpoints from setpoints.json: {self.targets}")
            
            except Exception as e:
                log.error(f"Failed to load setpoints from file: {e}")
        
        else:
            log.info("No setpoints.json file found. Using default values.")