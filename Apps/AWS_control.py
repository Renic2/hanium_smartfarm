# =================================================================================
# AWS_control.py
# AWS와 연결 담당
# =================================================================================


# 외부 모듈 호출
import threading
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
# MQTT 클라이언트를 위한 paho-mqtt 라이브러리
import paho.mqtt.client as mqtt
import json
import os

# 내부 모듈 호출
from Utility import log
import Config
from _System_ import SystemState

class AWSHandler:
    def __init__ (self, state: SystemState):
        self.state = state
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
        self.data = self.state.get_all_data()

        #MQTT 클랄이언트 설정
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smartfarm-pi-hanium")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        home_dir = os.path.expanduser("~")

        certs_path = os.path.join(home_dir, "AWS/Imp")

        self.ca_path = os.path.join(certs_path, "AmazonRootCA1.pem")
        self.cert_path = os.path.join(certs_path, "0bc986e09690058b5d04735400aac0aed3c881b583d12293e91d2dc4abfdc261-certificate.pem.crt")
        self.key_path = os.path.join(certs_path, "0bc986e09690058b5d04735400aac0aed3c881b583d12293e91d2dc4abfdc261-private.pem.key")
        self.mqtt_endpoint = "a16umr8elu8e4g-ats.iot.ap-northeast-2.amazonaws.com"
        self.mqtt_client.tls_set(ca_certs=self.ca_path, certfile=self.cert_path, keyfile=self.key_path)
        
        self.stop_event = threading.Event()

    def upload_to_s3(self, local_file_path: str, s3_object_name: str) -> bool:
        # 지정 파일을 S3 버킷에 업로드
        try:
            log.info(f"Uploading {local_file_path} to S3 bucket '{Config.AWS_S3_BUCKET_NAME}' as '{s3_object_name}'")
            self.s3_client.upload_file(local_file_path, Config.AWS_S3_BUCKET_NAME, s3_object_name)
            log.info("S3에 성공적으로 업로드하였습니다.")
            return True
        
        except FileNotFoundError:
            log.error(f"S3 업로드 실패: 파일을 {local_file_path}에서 찾지 못하였습니다.")
            return False
        
        except (NoCredentialsError, PartialCredentialsError):
            log.error("S3 업로드 실패: AWS 인증서 확인 실패. 다시 구성해주세요.")
            return False
        
        except Exception as e:
            log.error(f"S3에 업로드 중 오류가 발생하였습니다: {e}")
            return False
        
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties):
        """MQTT 브로커에 연결되었을 때 실행되는 콜백 함수."""
        if rc == 0:
            log.info("Connected to AWS IoT Core successfully.")
            # 분석 결과가 전송될 토픽을 구독
            topic = "smartfarm/analysis/result"
            client.subscribe(topic)
            log.info(f"Subscribed to MQTT topic: '{topic}'")
        
        else:
            log.error(f"Failed to connect to AWS IoT Core, return code {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        """구독 중인 토픽에 메시지가 도착했을 때 실행되는 콜백 함수."""
        try:
            payload = msg.payload.decode('utf-8')
            log.info(f"Received message from topic '{msg.topic}': {payload}")
            
            data = json.loads(payload)
            new_condition = data.get("status")
            
            if new_condition:
                # SystemState의 상태를 직접 수정하지 않고, 상태 변경 메서드를 통해 업데이트
                with self.state.file_lock:
                    self.data["PLANT_CONDITION"] = new_condition
                log.info(f"식물 컨디션이 변경되었습니다: '{new_condition}'")

        except Exception as e:
            log.error(f"MQTT 파일 처리중 오류 발생: {e}")

    def start_mqtt_listener(self):
        # MQTT 리스너를 시작하여 분석 결과를 비동기적으로 수신 대기합니다.
        # mqtt_endpoint, root CA 인증서, device 인증서, 개인키 존재시 아래 주석 해제
        try:
            log.info("MQTT 브로커에 연겷을 시도합니다.")
            self.mqtt_client.connect(self.mqtt_endpoint, 8883)
            self.mqtt_client.loop_start() 
        
        except Exception as e:
            log.error(f"MQTT connection failed: {e}. Please check endpoint and certificates.")
        log.warning("MQTT listener is currently disabled. Please configure certificates and endpoint in aws_handler.py.")

    def stop_mqtt_listener(self):
        # MQTT 리스너를 중지합니다.
        if self.mqtt_client.is_connected():
            log.info("Stopping MQTT listener...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            log.info("MQTT listener stopped.")
