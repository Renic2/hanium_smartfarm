# -----------------------------------------------------------------------
# config.py
# 시스템 전반에 사용되는 설정 값들을 저장한 파일
# 환경에 맞도록 수정하여 사용
# -----------------------------------------------------------------------


# Serial 통신 설정
SERIAL_PORT = None
BAUD_RATE = 9600 # 통신 속도, 아두이노와 동일하게 설정

# 하드웨어 연결 확인 설정
HEARTBEAT_INTERVAL = 5 # 아두이노에서 전송하는 하트비트 간격 (초)
HEARTBEAT_TIMEOUT = 10 # HEARTBEAT 신호가 없을 때 타임아웃 (초)

# 자동 제어 목표
TARGET_TEMP = 25.0 # 자동 제어 목표 온도 (섭씨)
TARGET_SOIL_MOISTURE = 400 # 자동 제어 목표 토양 습도

# PID 게인 설정
PID_KP = 5.0 # 비례 게인
PID_KI = 0.1 # 적분 게인
PID_KD = 10.0 # 미분 게인

# API 보안 설정 
API_SECRET_KEY = "HANIUMA20K197WS3STECH21SAFE75E9O" # 임시 키, 변경 가능

# AWS 설정
AWS_REGION = "ap-northeast-2" # AWS 리전
AWS_S3_BUCKET_NAME = "receivedphotohanium2025smartfarm" # S3 버킷 이름

# LOGGING 설정
LOG_DIRECTORY = "logs" # 로그 파일 저장 디렉토리
LOG_FILE_MAX_BYTES = 1024 * 1024 * 10 # 로그 파일 최대 크기 (10MB)
LOG_FILE_BACKUP_COUNT = 5 # 로그 파일 백업 최대 개수