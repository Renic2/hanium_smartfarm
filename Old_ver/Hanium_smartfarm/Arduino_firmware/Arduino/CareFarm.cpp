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
  // 보내는 포맷 - sensor:(TEMP),(SOIL),(HUMID),(LIGHT)
  // 예시 포맷 - sensor:25.5,300,45,1000
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
    doc["TYPE"] = "HEARTBEAT:";
    serializeJson(doc, Serial);
    Serial.println();
}

// 라즈베리파이로부터 받은 명령 처리
void CareFarm::processSerialCommand(String cmd){
  cmd.trim();
  char buf[32];
  cmd.toCharArray(buf, sizeof(buf)); // 문자열을 char 배열로 변환

  char *token = strtok(buf, ","); // strtok으로 분리
  int FAN_SPEED = atoi(token);    // 첫 번째 토큰을 정수로 변환
  if (FAN_SPEED > 0)
  {
    analogWrite(COOLING_FAN_PIN, FAN_SPEED); // 팬 속도 설정
  }
  else
  {
    digitalWrite(COOLING_FAN_PIN, LOW); // 팬 끄기
  }

  token = strtok(NULL, ",");    // 다음 토큰으로 이동
  int PUMP_SPEED = atoi(token); // 두 번째 토큰을 정수로 변환
  if (PUMP_SPEED > 0)
  {
    analogWrite(WATER_PUMP_PIN, PUMP_SPEED); // 펌프 속도 설정
  }
  else
  {
    digitalWrite(WATER_PUMP_PIN, LOW); // 펌프 끄기
  }

  token = strtok(NULL, ",");         // 다음 토큰으로 이동
  int LED_PLANT_STATE = atoi(token); // 세 번째 토큰을 정수로 변환
  if (LED_PLANT_STATE == 1)
  {
    digitalWrite(LED_PLANT_PIN, HIGH); // 식물 LED 켜기
  }
  else
  {
    digitalWrite(LED_PLANT_PIN, LOW); // 식물 LED 끄기
  }

  token = strtok(NULL, ",");         // 다음 토큰으로 이동
  int LED_LIGHT_STATE = atoi(token); // 네 번째 토큰을 정수로 변환
  if (LED_LIGHT_STATE == 1)
  {
    digitalWrite(LED_LIGHT_PIN, HIGH); // 조명 LED 켜기
  }
  else
  {
    digitalWrite(LED_LIGHT_PIN, LOW); // 조명 LED 끄기
  }

  token = strtok(NULL, ",");           // 다음 토큰으로 이동
  int THERMAL_PAD_STATE = atoi(token); // 다섯 번째 토큰을 정수로 변환
  if (THERMAL_PAD_STATE == 1)
  {
    digitalWrite(THERMAL_PAD_PIN, HIGH); // 열 패드 켜기
  }
  else
  {
    digitalWrite(THERMAL_PAD_PIN, LOW); // 열 패드 끄기
  }
}