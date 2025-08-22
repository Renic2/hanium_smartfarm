#ifndef CAREFARM_H
#define CAREFARM_H

#include <Arduino.h>
#include <DHT.h>
#include <BH1750.h>

// 센서 데이터 구조체
struct SensorData {
    float temperature;
    float humidity;
    int soilMoisture;
    float lightLevel;
};

class CareFarm {
public:
    CareFarm(); // 생성자
    void initialize(); // 초기화 함수 통합
    SensorData readSensors();
    void readAndSendSensors(); // 센서 읽고 JSON으로 전송
    void sendHeartbeat(); // Heartbeat 전송
    void processSerialCommand(String cmd); // 시리얼 명령 수신 및 처리

private:
    // --- 핀 번호 정의 ---
    const int SOIL_MOISTURE_PIN = A0;
    const int DHT_PIN = 2;
    const int COOLING_FAN_PIN = 3;
    const int WATER_PUMP_PIN = 5;
    const int LED_LIGHT_PIN = 4;
    const int LED_PLANT_PIN = 6;
    const int THERMAL_PAD_PIN = 7;

    // --- 라이브러리 객체 ---
    DHT dht;
    BH1750 lightMeter;
};

#endif