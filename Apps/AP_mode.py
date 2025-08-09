# =================================================================================
# Ap_mode.py
# 인터넷 연결을 확인하고 라즈베리의 ap 모드를 활성화하는 파일
# =================================================================================


# 외부 모듈 호출
import subprocess
import time
import os 
import sys

# 내부 모듈 호출
from Utility import log

# 인터넷 연결 확인
def check_internet_connection():
    try:
        subprocess.check_output(["ping", "-c", "1", "8.8.8.8"]) # 구글 dns로 핑을 보내 연결 확인
        log.info("인터넷 연결이 되었습니다.")
        return True

    except subprocess.CalledProcessError:
        log.warning("인터넷 연결에 실패하였습니다.")
        return False

# AP 모드 시작    
def start_ap_mode_services():
    log.info("AP 모드를 시작합니다.")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "dhcpcd"])
        time.sleep(5)
        subprocess.run(["sudo", "systemctl", "start", "hostapd"])
        subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])
        log.info("AP mode services started successfully.")
    
    except Exception as e:
        log.error(f"AP 모드 실행에 실패하였습니다: {e}")

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
        log.info("API 서버를 여는 중입니다. AP 모드를 시작합니다.")
        
        # api.py를 --ap-mode 인자와 함께 실행
        api_script_path = os.path.join(script_dir, "api.py")
        subprocess.run([python_executable, api_script_path, "--ap-mode"])
    
    else:
        # 인터넷 연결 성공: 메인 스마트팜 애플리케이션 시작 
        log.info("스마트팜 어플리케이션을 시작합니다.")
        
        # main.py를 별도의 프로세스로 실행
        main_script_path = os.path.join(script_dir, "main.py")
        subprocess.run([python_executable, main_script_path])

        log.info("네트워크 체크가 끝났습니다. 다음 단계로 진행합니다.")