# =================================================================================
# Utility.py
# Log 저장, PID 함수 등 보조 함수들을 모아둔 파일
# =================================================================================


# 외부 모듈 호출
import os
import logging
from logging.handlers import RotatingFileHandler
import time

# 내부 모듈 호출
import Config

# 로그의 레벨을 필터링하는 클래스
class LevelFilter(logging.Filter):
    def __init__(self, level):
        super().__init__()
        self.level = level

    def filter(self, record):
        return record.levelno == self.level

def setup_logger():
    # 시스템 로깅 설정 초기화 후, 로거 객체 변환
    if not os.path.exists(Config.LOG_DIRECTORY):
        os.makedirs(Config.LOG_DIRECTORY)

    # LOGGER 객체 생성
    LOGGER = logging.getLogger("smartfarm_logger")
    LOGGER.setLevel(logging.DEBUG) # 로그 레벨 설정 (전체)

    # 핸들러 설정이 존재한다면 중복을 추가 방지
    if LOGGER.hasHandlers():
        return LOGGER
    
    # 로그 포맷 설정
    FORMATTER = logging.Formatter(
        '[%(asctime)s] - [%(levelname)s] - [%(message)s]',
        datefmt= '%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 출력 핸들러
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(FORMATTER)
    LOGGER.addHandler(stream_handler)

    # 로그 레벨 목록
    log_levels = {
        'debug' : logging.DEBUG,
        'info' : logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    # 각 레벨별 핸들러를 생성 
    for level_name, level_value in log_levels.items():
        file_path = os.path.join(Config.LOG_DIRECTORY, f"{level_name}.log")
        handler = RotatingFileHandler(
            filename = file_path,
            maxBytes = Config.LOG_FILE_MAX_BYTES,
            backupCount = Config.LOG_FILE_BACKUP_COUNT,
            encoding = 'utf-8'
        )
        handler.setLevel(logging.DEBUG)             # 전체 호출
        handler.addFilter(LevelFilter(level_value)) # 필요 레벨만
        handler.setFormatter(FORMATTER)
        LOGGER.addHandler(handler)

    LOGGER.info("="*20 + "LOGGER SETUP COMPLETE" + "="*20)

    return LOGGER

# 프로그램의 다른 파일에서 이 로거를 가져와 사용 가능한 인스턴스
log = setup_logger()


# PID 함수 (현재는 온도 조절에 사용)
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