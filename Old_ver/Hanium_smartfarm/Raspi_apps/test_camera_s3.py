# =================================================================
# test_camera_s3.py
# -----------------------------------------------------------------
# CLI 카메라 촬영 및 S3 업로드 기능만 독립적으로 테스트하는 스크립트.
# =================================================================

from util import log
from aws_handler import AWSHandler
from camera_handler import CameraHandler

class DummyHardwareController:
    """
    테스트를 위한 가짜 하드웨어 컨트롤러입니다.
    실제 시리얼 통신 없이, 어떤 명령을 보내는지 로그로만 출력합니다.
    """
    def send_command(self, device: str, value: int):
        log.info(f"[DUMMY_HW] Sending command -> DEVICE: {device}, VALUE: {value}")

if __name__ == "__main__":
    log.info("=" * 20 + " Camera to S3 Upload Test " + "=" * 20)
    
    # 1. 테스트에 필요한 객체들을 생성합니다.
    # SystemState는 AWSHandler 초기화에 필요하지만, 이 테스트에서는 직접 사용되지 않습니다.
    # 따라서 가짜(None) 객체를 전달해도 무방합니다.
    dummy_state = None
    dummy_hardware = DummyHardwareController()
    aws_handler = AWSHandler(dummy_state)
    camera_handler = CameraHandler(dummy_hardware, aws_handler)

    log.info("Test components initialized. Starting capture sequence...")

    try:
        # 2. 메인 기능인 사진 촬영 및 업로드 함수를 호출합니다.
        camera_handler.capture_and_upload()
    except Exception as e:
        log.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        log.info("=" * 20 + " Test Finished " + "=" * 20)