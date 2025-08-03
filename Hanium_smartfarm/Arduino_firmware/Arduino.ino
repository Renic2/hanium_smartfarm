#include "CareFarm.h"

CareFarm carefarm; // CareFarm 객체 생성

unsigned long last_sensor_read_time = 0;
unsigned long last_heartbeat_time = 0;

void setup() {
    Serial.begin(9600);
    carefarm.initialize();
}

void loop() {
    unsigned long current_time = millis();

    // 2초마다 센서 데이터 읽고 전송
    if (current_time - last_sensor_read_time >= 2000) {
        last_sensor_read_time = current_time;
        carefarm.readAndSendSensors();
    }

    // 5초마다 Heartbeat 전송
    if (current_time - last_heartbeat_time >= 5000) {
        last_heartbeat_time = current_time;
        carefarm.sendHeartbeat();
    }

    // 시리얼 명령은 항상 확인
    carefarm.processSerialCommand();
}