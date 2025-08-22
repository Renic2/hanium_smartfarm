# =================================================================================
# _System_.py
# 시스템의 실시간 상태와 동적 설정을 관리하는 중앙 저장소
# 여러 스레드에서 안전한 접근을 위하여 LOCK 사용
# =================================================================================

import threading
import json
import os
from datetime import datetime
from Utility import log

class SystemState:
    def __init__(self, filepath="Value.json"):
        self.filepath = filepath
        self.file_lock = threading.Lock()
        self.last_updated = None
        if not os.path.exists(self.filepath):
            self._initialize_json()

    def _initialize_json(self):
        initial_data = {
            "TARGET": {"TARGET_TEMP": 25.0, "TARGET_SOIL_MOISTURE": 400},
            "SENSOR": {"TEMP": 0.0, "HUMID": 0.0, "SOIL": 0.0, "LIGHT": 0.0},
            "ACTUATOR": {"FAN": 0, "PUMP": 0, "HEAT_PANNEL": 0, "GROW_LIGHT": 1, "WHITE_LED": 0},
            "MODE": "AUTO",
            "PLANT_CONDITION": "NORMAL"
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
        log.info(f"새로운 json 파일이 {self.filepath}에 생성되었습니다.")

    def _write_state(self, data):
        with self.file_lock:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.last_updated = datetime.now()

    def get_all_data(self):
        with self.file_lock:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                log.error(f"데이터 불러오는 중 오류가 생겼습니다: {e}")
                self._initialize_json()
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)

    def update_values(self, update_data: dict):
        with self.file_lock:
            current_data = self.get_all_data()
            is_updated = False

            if 'MODE' in update_data and update_data['MODE'] in ['AUTO', 'MANUAL']:
                if current_data['MODE'] != update_data['MODE']:
                    current_data['MODE'] = update_data['MODE']
                    is_updated = True
                    # 수동 모드로 바뀔 때 안전을 위해 팬, 펌프, 히터를 끔
                    if update_data['MODE'] == 'MANUAL':
                        current_data['ACTUATOR']['FAN'] = 0
                        current_data['ACTUATOR']['PUMP'] = 0
                        current_data['ACTUATOR']['HEAT_PANNEL'] = 0

            if 'TARGET' in update_data and isinstance(update_data['TARGET'], dict):
                current_data['TARGET'].update(update_data['TARGET'])
                is_updated = True

            # ★★★ 핵심 수정: 'AUTO' 모드일 때도 업데이트 허용 ★★★
            if 'ACTUATOR' in update_data and isinstance(update_data['ACTUATOR'], dict):
                # API를 통한 수동 제어는 'MANUAL' 모드일 때만 허용
                if current_data['MODE'] == 'MANUAL':
                    current_data['ACTUATOR'].update(update_data['ACTUATOR'])
                    is_updated = True
                # 자동 제어 로직은 'AUTO' 모드일 때만 허용
                elif current_data['MODE'] == 'AUTO':
                    current_data['ACTUATOR'].update(update_data['ACTUATOR'])
                    is_updated = True
                else:
                    log.warning("ACTUATOR 업데이트가 무시되었습니다.")


            if is_updated:
                self._write_state(current_data)
                log.info("시스템 상태가 업데이트 되었습니다.")

            return current_data