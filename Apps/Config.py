# =================================================================================
# Config.py
# 시스템 전체에서 사용될 설정 값들을 저장한 파일
# 시스템 완성 후, 환경 변경이 필요할 때 이 파일 수정
# 모든 변수는 대문자로 통일한다.
# =================================================================================


# Serial 통신 설정
SERIAL_PORT = None  # 시리얼 탐색 후 설정하기에 None
BAUD_RATE = 9600    # 통신 속도 지정, 아두이노와 동일하게 설정

# 하드웨어 연결 확인을 위한 설정 (Arduino <-> Rasberry Pi)
HEARTBEAT_INTERVAL = 5  # 아두이노에서 전송하는 신호 간격 (초)
HEARTBEAT_TIMEOUT = 15  # 하드웨어 연결이 끊김을 판단하는 시간 (초)

# 자동 제어 목표
TARGET_TEMP = 25.0          # 목표 온도 (섭씨)
TARGET_SOIL_MOISTURE = 400  # 목표 토양 습도

# PID 게인 설정 (float 사용)
PID_KP = 5.0    # 비례 게인
PID_KI = 0.1    # 적분 게인
PID_KD = 10.0   # 미분 게인

# API 보안 설정
# 임시 키, 변경 가능
API_SECRET_KEY = "HANIUMA20K197WS3STECH21SAFE75E9O"

# AWS 설정
AWS_REGION = "ap-northeast-2"                           # AWS 리전
AWS_S3_BUCKET_NAME = "receivedphotohanium2025smartfarm" # S3 버킷 이름

# LOGGING 설정
LOG_DIRECTORY = "logs"                  # 로그 파일 저장 디렉토리
LOG_FILE_MAX_BYTES = 1024 * 1024 * 10   # 로그 파일 최대 크기 (10MB)
LOG_FILE_BACKUP_COUNT = 5               # 로그 파일 백업 최대 개수

# 제어 설정
RECONNECT_DELAY = 2
CONTROL_INTERVAL = 2