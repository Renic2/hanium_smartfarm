# -----------------------------------------------------------------------
# util.py
# 프로젝트에서 사용할 보조 함수를 모아둔 파일
# LOGGING 설정이 대표
# -----------------------------------------------------------------------

import os 
import logging
from logging.handlers import RotatingFileHandler
import config
import time 

def setup_logger():
    # 시스템 로깅 설정 초기화 후 로거 객체 반환

    if not os.path.exists(config.LOG_DIRECTORY):
        os.makedirs(config.LOG_DIRECTORY)

    # 로거 객체 생성
    LOGGER = logging.getLogger("smartfarm_logger")
    LOGGER.setLevel(logging.INFO) # 로그 레벨 설정 (INFO 이상만)

    # 이미 핸들러 설정되어 있다면 중복 추가 방지
    if LOGGER.hasHandlers():
        return LOGGER
    
    FORMATTER = logging.Formatter(
        '[%(asctime)s] - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. 콘솔 출력용 핸들러
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setFormatter(FORMATTER)
    LOGGER.addHandler(STREAM_HANDLER)

    # 2. 파일 출력용 핸들러
    LOG_FILE_PATH = os.path.join(config.LOG_DIRECTORY, "smartfarm.log")
    FILE_HANDLER = RotatingFileHandler(
        filename=LOG_FILE_PATH, 
        maxBytes=config.LOG_FILE_MAX_BYTES,
        backupCount=config.LOG_FILE_BACKUP_COUNT,
        encoding='utf-8'
    )
    
    FILE_HANDLER.setFormatter(FORMATTER)
    LOGGER.addHandler(FILE_HANDLER)

    LOGGER.info("="*20 + " LOGGER SETUP COMPLETE " + "="*20)

    return LOGGER

# 프로그램의 다른 파일에서 이 로거를 가져와 사용 가능한 인스턴스
log = setup_logger()

class PID:
    def __init__(self, Kp, Ki, Kd, setpoint):
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.last_error, self.integral = 0.0, 0.0
        self.last_time = time.time()

    def compute(self, measured_value):
        current_time = time.time()
        dt = current_time - self.last_time

        if dt <= 0: return 0

        error = self.setpoint - measured_value
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        
        self.last_error = error
        self.last_time = current_time
        
        return output