# -----------------------------------------------------------------------
# aws_handler.py
# AWS와의 모든 연동을 담당하는 클래스
# 사진을 S3 버킷에 업로드, IoT Core(MQTT)를 통해 분석 결과를 수신
# -----------------------------------------------------------------------

import threading
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
# MQTT 클라이언트를 위한 paho-mqtt 라이브러리 필요
import paho.mqtt.client as mqtt
import json
import os

from util import log
import config
from system_state import SystemState

class AWSHandler:
    def __init__(self, state: SystemState):
        self.state = state
        self.s3_client = boto3.client('s3', region_name=config.AWS_REGION)

        # MQTT 클라이언트 설정
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smartfarm-pi-hanium")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message

        # 실제 운영시 필요
        # AWS IoT Core에서 발급받은 인증서 파일들의 정확한 경로 설정
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
            log.info(f"Uploading {local_file_path} to S3 bucket '{config.AWS_S3_BUCKET_NAME}' as '{s3_object_name}'")
            self.s3_client.upload_file(local_file_path, config.AWS_S3_BUCKET_NAME, s3_object_name)
            log.info("S3 Upload successful.")
            return True
        
        except FileNotFoundError:
            log.error(f"S3 Upload failed: File not found at {local_file_path}")
            return False
        
        except (NoCredentialsError, PartialCredentialsError):
            log.error("S3 Upload failed: AWS credentials not found. Please configure them (e.g., via 'aws configure').")
            return False
        
        except Exception as e:
            log.error(f"An unexpected error occurred during S3 upload: {e}")
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
                with self.state.lock:
                    self.state.plant_condition = new_condition
                log.info(f"Plant condition in SystemState updated to: '{new_condition}'")

        except Exception as e:
            log.error(f"Error processing MQTT message: {e}")

    def start_mqtt_listener(self):
        # MQTT 리스너를 시작하여 분석 결과를 비동기적으로 수신 대기합니다.
        # mqtt_endpoint, root CA 인증서, device 인증서, 개인키 존재시 아래 주석 해제
        try:
            log.info("Attempting to connect to MQTT broker...")
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
