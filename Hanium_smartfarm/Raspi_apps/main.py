# -----------------------------------------------------------------------
# main.py
# 스마트팜 애플리케이션의 메인 진입점 (Entry point)
# 모든 요소(컴포넌트) 초기화, 스레드 시작, API 서버 실행
# -----------------------------------------------------------------------

import signal
from util import log
from system_state import SystemState
from hardware_control import HardwareController
from auto_controller import AutoController
from aws_handler import AWSHandler
from camera_handler import CameraHandler
from api import run_api_server

# 전역 인스턴스
# 애플리케이션의 핵심 컴포넌트들을 담을 변수
state: SystemState = None
hardware: HardwareController = None
auto_control: AutoController = None
aws: AWSHandler = None
cam: CameraHandler = None

def graceful_shutdown(signum, frame):
    """Ctrl+C와 같은 종료 신호를 받았을 때 안전하게 종료하는 함수."""
    log.info("Shutdown signal received. Cleaning up...")
    
    if auto_control:
        auto_control.stop()
    if hardware:
        hardware.stop()
    if aws:
        aws.stop_mqtt_listener()
    
    log.info("All components stopped. Exiting now.")
    exit(0)

if __name__ == "__main__":
    log.info("=" * 20 + " Smartfarm Application Starting Up " + "=" * 20)

    # 안전 종료 핸들러 등록
    # Ctrl+C (SIGINT) 신호를 받으면 graceful_shutdown 함수를 실행
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    try:
        # 핵심 컴포넌트 객체 생성
        # 의존성 순서에 따라 객체를 생성
        log.info("Initializing core components...")
        state = SystemState()
        hardware = HardwareController(state)
        aws = AWSHandler(state)
        cam = CameraHandler(hardware, aws)
        auto_control = AutoController(state, hardware)
        log.info("All components initialized.")

        # 백그라운드 스레드 시작
        # 하드웨어 통신과 자동 제어는 백그라운드에서 계속 실행
        hardware.start()
        auto_control.start()
        
        # AWS MQTT 리스너 시작 (인증서 설정 후 주석 해제 필요)
        aws.start_mqtt_listener()
        
        # API 서버 실행
        # 이 함수는 프로그램이 종료될 때까지 블로킹(Blocking) 상태로 실행
        # 이 함수가 메인 스레드를 차지
        run_api_server(
            state_instance=state,
            hardware_instance=hardware,
            camera_instance=cam
        )

    except Exception as e:
        log.error(f"An unhandled error occurred in main: {e}", exc_info=True)
    finally:
        log.info("=" * 20 + " Smartfarm Application Shutting Down " + "=" * 20)
