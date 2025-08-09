# network_switcher.py
import subprocess
import time
import os

# main.py와 api.py가 있는 폴더로 경로 맞추기
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from util import log

def check_internet_connection():
    # 인터넷 연결 확인
    try:
        # 8.8.8.8 (Google DNS)로 핑을 보내 연결 확인
        subprocess.check_output(["ping", "-c", "1", "8.8.8.8"])
        log.info("Internet connection successful.")
        return True
    
    except subprocess.CalledProcessError:
        log.warning("Internet connection failed.")
        return False

def start_ap_mode_services():
    # AP 모드 시작
    log.info("Starting AP mode...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "dhcpcd"])
        time.sleep(5)
        subprocess.run(["sudo", "systemctl", "start", "hostapd"])
        subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])
        log.info("AP mode services started successfully.")
    
    except Exception as e:
        log.error(f"Failed to start AP mode services: {e}")

if __name__ == '__main__':
    log.info("=" * 20 + " Network Switcher Starting " + "=" * 20)
    time.sleep(10) # 부팅 직후 네트워크 안정화를 위한 대기

    # 스크립트가 있는 폴더 경로
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 가상환경의 파이썬 실행 파일 경로
    python_executable = f"/home/hanium/venv-libcamera/bin/python"

    if not check_internet_connection():
        # 인터넷 연결 실패: AP 모드 시작 
        start_ap_mode_services()
        log.info("Launching API server in AP Mode...")
        
        # api.py를 --ap-mode 인자와 함께 실행
        api_script_path = os.path.join(script_dir, "api.py")
        subprocess.run([python_executable, api_script_path, "--ap-mode"])
    
    else:
        # 인터넷 연결 성공: 메인 스마트팜 애플리케이션 시작 
        log.info("Starting main smartfarm application...")
        
        # main.py를 별도의 프로세스로 실행
        main_script_path = os.path.join(script_dir, "main.py")
        subprocess.run([python_executable, main_script_path])

        log.info("Network switcher process finished.")