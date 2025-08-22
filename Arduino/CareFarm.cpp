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

    // 센서 핀 모드 설정
    pinMode(SOIL_MOISTURE_PIN, INPUT);

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

// 센서 데이터 읽기 함수
SensorData CareFarm::readSensors(){
  SensorData data;

  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  data.soilMoisture = analogRead(SOIL_MOISTURE_PIN);
  data.lightLevel = lightMeter.readLightLevel();

  // 센서 데이터값 시리얼 전송
  // 보내는 포맷 - SENSOR:(TEMP),(SOIL),(HUMID),(LIGHT)
  // 예시 포맷 - SENSOR:25.5,300,45,1000
  Serial.print("SENSOR:");
  Serial.print(data.temperature);
  Serial.print(",");
  Serial.print(data.soilMoisture);
  Serial.print(",");
  Serial.print(data.humidity);
  Serial.print(",");
  Serial.println(data.lightLevel);

  return data;
}

// Heartbeat 신호 전송
void CareFarm::sendHeartbeat() {
    JsonDocument doc;
    Serial.println( "HEARTBEAT:");
}

// 라즈베리파이로부터 받은 명령 처리
void CareFarm::processSerialCommand(String cmd) {
  cmd.trim();
  char buf[32];
  cmd.toCharArray(buf, sizeof(buf));
  
  // 핀 배열과 제어 타입 배열
  int pins[] = {COOLING_FAN_PIN, WATER_PUMP_PIN, LED_PLANT_PIN, LED_LIGHT_PIN, THERMAL_PAD_PIN};
  bool isAnalog[] = {true, true, false, false, false};
  
  char *token = strtok(buf, ",");
  
  for (int i = 0; i < 5 && token != NULL; i++) {
    int value = atoi(token);
    
    if (isAnalog[i]) {
      analogWrite(pins[i], value > 0 ? value : 0);
      if (value == 0) digitalWrite(pins[i], LOW);
    } else {
      digitalWrite(pins[i], value == 1 ? HIGH : LOW);
    }
    
    token = strtok(NULL, ",");
  }
}
