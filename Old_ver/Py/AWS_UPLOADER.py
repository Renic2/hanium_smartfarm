import os
import time
import datetime
import boto3
import logging
from botocore.exceptions import NoCredentialsError

# AWS 설정
ACCESS_KEY = "YOUR_ACCESS_KEY"
SECRET_KEY = "YOUR_SECRET_KEY"
REGION = "ap-northeast-2"
BUCKET_NAME = "your-s3-bucket-name"

# 로그 설정
os.makedirs("logs", exist_ok=True)
log_file = datetime.datetime.now().strftime("logs/log_%Y-%m-%d.txt")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# S3 업로드 함수
def upload_to_s3(local_path, s3_path):
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            region_name=REGION
        )
        s3.upload_file(local_path, BUCKET_NAME, s3_path)
        logging.info(f"[업로드 완료] {s3_path}")
        return True
    except FileNotFoundError:
        logging.error(f"[파일 없음] {local_path}")
    except NoCredentialsError:
        logging.error("[AWS 인증 오류]")
    return False

# 카메라 촬영 + 업로드
def capture_and_upload():
    os.makedirs("captured", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"captured/{timestamp}.jpg"
    s3_path = f"photos/{timestamp}.jpg"

    # 촬영
    cmd = f"libcamera-still -n -o {filename} --width 640 --height 480 --nopreview"
    result = os.system(cmd)

    if result == 0:
        logging.info(f"[촬영 완료] {filename}")
        if upload_to_s3(filename, s3_path):
            os.remove(filename)
            logging.info(f"[삭제 완료] {filename}")
    else:
        logging.error(f"[촬영 실패] 명령어: {cmd}")

# 루프 (주기적 촬영)
if __name__ == "__main__":
    INTERVAL_SEC = 60 * 5  # 5분마다 촬영

    while True:
        capture_and_upload()
        time.sleep(INTERVAL_SEC)