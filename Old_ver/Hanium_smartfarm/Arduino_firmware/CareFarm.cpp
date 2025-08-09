#include "CareFarm.h"
#include <ArduinoJson.h>
#include <Wire.h>

// 생성자: 객체가 생성될 때 dht 객체를 초기화
CareFarm::CareFarm() : dht(DHT_PIN, DHT22) {}

// 모든 초기화를 담당하는 함수
void CareFarm::initialize() {
    // 센서 초기화
    Wire.begin();
    dht.begin();
    lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
    
    pinMode(SOIL_MOISTURE_PIN, INPUT);
    pinMode(DHT_PIN, INPUT);
     
    // 액추에이터 핀 모드 설정
    pinMode(THERMAL_PAD_PIN, OUTPUT);
    pinMode(COOLING_FAN_PIN, OUTPUT);
    pinMode(WATER_PUMP_PIN, OUTPUT);
    pinMode(LED_LIGHT_PIN, OUTPUT);
    pinMode(LED_PLANT_PIN, OUTPUT);

    // 모든 액추에이터 초기 상태 OFF
    digitalWrite(THERMAL_PAD_PIN, LOW);
    analogWrite(COOLING_FAN_PIN, 0);
    analogWrite(WATER_PUMP_PIN, 0);
    digitalWrite(LED_LIGHT_PIN, LOW);
    digitalWrite(LED_PLANT_PIN, LOW);
}

// 센서 값을 읽어 JSON으로 시리얼 전송
void CareFarm::readAndSendSensors() {
    JsonDocument doc; // ArduinoJson 7.x 버전 기준

    doc["temp"] = dht.readTemperature();
    doc["humid"] = dht.readHumidity();
    doc["soil"] = analogRead(SOIL_MOISTURE_PIN);
    doc["light"] = lightMeter.readLightLevel();

    // NaN 값 체크 (센서 읽기 실패 시)
    if (isnan(doc["temp"].as<float>()) || isnan(doc["humid"].as<float>())) {
        return; // 읽기 실패 시 전송 안 함
    }

    serializeJson(doc, Serial);
    Serial.println();
}

// Heartbeat 신호 전송
void CareFarm::sendHeartbeat() {
    JsonDocument doc;
    doc["TYPE"] = "HEARTBEAT";
    serializeJson(doc, Serial);
    Serial.println();
}

// 라즈베리파이로부터 받은 JSON 명령 처리
void CareFarm::processSerialCommand() {
    if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, cmd);

        if (error) {
            return; // JSON 파싱 실패 시 무시
        }

        const char* device = doc["DEVICE"];
        int value = doc["VALUE"];

        if (strcmp(device, "FAN") == 0) {
            analogWrite(COOLING_FAN_PIN, value);
        } else if (strcmp(device, "PUMP") == 0) {
            analogWrite(WATER_PUMP_PIN, value);
        } else if (strcmp(device, "HEAT_PANNEL") == 0) {
            digitalWrite(THERMAL_PAD_PIN, value == 1 ? HIGH : LOW);
        } else if (strcmp(device, "WHITE_LED") == 0) {
            digitalWrite(LED_LIGHT_PIN, value == 1 ? HIGH : LOW);
        } else if (strcmp(device, "GROW_LIGHT") == 0) {
            digitalWrite(LED_PLANT_PIN, value == 1 ? HIGH : LOW);
        }
    }
}