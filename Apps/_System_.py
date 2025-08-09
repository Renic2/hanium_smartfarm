# =================================================================================
# _System_.py
# 시스템의 실시간 상태와 동적 설정을 관리하는 중앙 저장소
# 여러 스레드에서 안전한 접근을 위하여 LOCK 사용
# =================================================================================


# 외부 모듈 호출
import threading
import json
import os
from datetime import datetime

# 내부 모듈 호출
from Utility import log

class SystemState:  # 시스템의 현재 상태와 설정 관리
    def __init__(self, filepath="value.json"):
        self.filepath = filepath
        self.file_lock = threading.Lock() # 파일에 여러 스레드가 접근하는 것을 방지
        self.last_updated = None

        # json 파일 존재 유무 확인
        if not os.path.exists(self.filepath):
            self._initialize_json()

    # json 데이터가 사라지면 초기 상태로 생성
    def _initialize_json(self):
        initial_data = {
            "TARGET": {"TARGET_TEMP": 25.0, "TARGET_SOIL_MOISTURE": 400},
            "SENSOR": {"TEMP": 0.0, "HUMID": 0.0, "SOIL": 0.0, "LIGHT": 0.0},
            "ACTUATOR": {"FAN": 0, "PUMP": 0, "HEAT_PANNEL": 0, "GROW_LIGHT": 1, "WHITE_LED": 0},
            "MODE": "AUTO",
            "PLANT_CONDITION": "NORMAL"
        }
        # 초기화는 파일에 직접 쓰는 것이 안전
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=4)
        log.info(f"새로운 json 파일이 {self.filepath}에 생성되었습니다.")

    # json 파일에 정보 저장, lock의 유무에 따라 저장하므로 안전하게 저장됨
    def _write_state(self, data):
        with self.file_lock:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.last_updated = datetime.now()
            
    #현재 설정 및 상태 데이터를 모두 읽어 반환
    def get_all_data(self):
        with self.file_lock:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                log.error(f"데이터 불러오는 중 오류가 생겼습니다: {e}")
                self._initialize_json()
                # 재귀 대신 다시 파일 열기
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)

    def update_values(self, update_data: dict):
        with self.file_lock:
            # 파일에서 직접 최신 데이터 읽기
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                log.error("업데이트 중 파일을 읽을 수 없어, 초기화 후 다시 시도합니다.")
                self._initialize_json()
                with open(self.filepath, "r", encoding="utf-8") as f:
                    current_data = json.load(f)

            # 메모리 상에서 데이터 수정 로직 수행
            is_updated = False
            if 'MODE' in update_data and update_data['MODE'] in ['AUTO', 'MANUAL']:
                if current_data['MODE'] != update_data['MODE']:
                    current_data['MODE'] = update_data['MODE']
                    is_updated = True

            if 'TARGET' in update_data and isinstance(update_data['TARGET'], dict):
                current_data['TARGET'].update(update_data['TARGET'])
                is_updated = True

            if 'ACTUATOR' in update_data and isinstance(update_data['ACTUATOR'], dict):
                if current_data['MODE'] == 'MANUAL':
                    current_data['ACTUATOR'].update(update_data['ACTUATOR'])
                    is_updated = True
                else:
                    log.warning("ACTUATOR 업데이트가 무시되었습니다: 현재 AUTO 모드입니다.")

            # 변경된 경우에만 파일에 최종 결과 한 번 쓰기
            if is_updated:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, ensure_ascii=False, indent=4)
                self.last_updated = datetime.now()
                log.info("시스템 상태가 업데이트 되었습니다.")

            return current_data