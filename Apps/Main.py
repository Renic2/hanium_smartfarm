# =================================================================================
# Main.py
# 스마트팜 app의 메인 진입점
# 모든 요소 초기화, 스레드 시작, API 서버 실행
# =================================================================================


# 외부 모듈 호출
import signal

# 내부 모듈 호출
from Utility import log
from _System_ import SystemState
from Arduino_control import HardwareController
from Auto_control import AutoController
from AWS_control import AWSHandler
from CLI_control import CameraHandler
from API import run_api_server

# 전역 인스턴스, 핵심 컴포넌트들을 담을 변수
state: SystemState = None
hardware: HardwareController = None
auto_control: AutoController = None
aws: AWSHandler = None
cli: CameraHandler = None

def graceful_shutdown(signum, frame):
    """Ctrl+C와 같은 종료 신호를 받았을 때 안전하게 종료하는 함수."""
    log.info("강제 종료를 인식하였습니다. 종료를 시작합니다.")
    
    if auto_control:
        auto_control.stop()
    if hardware:
        hardware.stop()
    if aws:
        aws.stop_mqtt_listener()
    if cli:
        cli.stop()
    
    log.info("모든 기능 정지. 이제 나가 주시길 바랍니다.")
    exit(0)

if __name__ == "__main__":
    log.info("=" * 20 + " 스마트팜 어플 시작 " + "=" * 20)

    # 안전 종료 핸들러 등록
    # Ctrl+C (SIGINT) 신호를 받으면 graceful_shutdown 함수를 실행
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    try:
        # 핵심 컴포넌트 객체 생성
        # 의존성 순서에 따라 객체를 생성
        log.info("중요 요소들을 초기화합니다.")
        state = SystemState()
        hardware = HardwareController(state)
        aws = AWSHandler(state)
        cli = CameraHandler(state, hardware, aws)
        auto_control = AutoController(state, hardware)
        log.info("모든 요소들이 초기화되엇습니다.")

        # 백그라운드 스레드 시작
        # 하드웨어 통신과 자동 제어는 백그라운드에서 계속 실행
        hardware.start()
        auto_control.start()
        cli.start()
        
        # AWS MQTT 리스너 시작 (인증서 설정 후 주석 해제 필요)
        aws.start_mqtt_listener()
        
        # API 서버 실행
        # 이 함수는 프로그램이 종료될 때까지 블로킹(Blocking) 상태로 실행
        # 이 함수가 메인 스레드를 차지
        run_api_server(
            state_instance=state,
            hardware_instance=hardware,
            camera_instance=cli
        ) 

    except Exception as e:
        log.error(f"An unhandled error occurred in main: {e}", exc_info=True)
    finally:
        log.info("=" * 20 + " Smartfarm Application Shutting Down " + "=" * 20)