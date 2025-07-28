#include <Arduino.h>
#include <DHT.h>
#include <Wire.h> // I2C 통신을 위한 라이브러리
#include <BH1750.h>
#include "CareFarm.h"

CareFarm::CareFarm()
{
  // 생성자에서 필요한 초기화 작업 수행
  dht = DHT(DHT_PIN, DHT22);
  lightMeter = BH1750();

  // 센서 핀 정의
  const int SOIL_MOISTURE_PIN = A0;
  const int COOLING_FAN_PIN = 3;
  const int DHT_PIN = 2;

  // 액추에이터 핀 정의
  const int WATER_PUMP_PIN = 4;
  const int LED_LIGHT_PIN = 5;
  const int LED_PLANT_PIN = 6;
  const int THERMAL_PAD_PIN = 7;

  // 센서 임계값
  const float TEMP_MIN = 15.0;
  const float TEMP_MAX = 22.0;
  const int SOIL_MOISTURE_MIN = 30;
  const int SOIL_MOISTURE_MAX = 700;
  // 타이밍 설정
  const int PUMP_DURATION = 5000;
  const int SENSOR_DELAY = 2000;

  // LED 밝기 설정
  const int LED_BRIGHTNESS = 100;
}

SensorData readSensors()
{
  SensorData data;

  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  data.soilMoisture = analogRead(SOIL_MOISTURE_PIN);
  data.lightLevel = lightMeter.readLightLevel();

  // 센서 데이터값 시리얼 전송
  // 보내는 포맷 - sensor:(TEMP),(SOIL),(HUMID),(LIGHT)
  // 예시 포맷 - sensor:25.5,300,45,1000
  Serial.print("sensor:");
  Serial.print(data.temperature);
  Serial.print(",");
  Serial.print(data.soilMoisture);
  Serial.print(",");
  Serial.print(data.humidity);
  Serial.print(",");
  Serial.println(data.lightLevel);

  return data;
}

// 센서 초기화 함수
void initializeSensors()
{
  Wire.begin();
  dht.begin();
  lightMeter.begin();
}

// 액추에이터 초기화 함수
void initializeActuators()
{
  pinMode(THERMAL_PAD_PIN, OUTPUT);
  pinMode(COOLING_FAN_PIN, OUTPUT);
  pinMode(WATER_PUMP_PIN, OUTPUT);
  pinMode(LED_LIGHT_PIN, OUTPUT);
  pinMode(LED_PLANT_PIN, OUTPUT);

  // 모든 액추에이터 초기 상태 설정
  digitalWrite(THERMAL_PAD_PIN, LOW);
  digitalWrite(COOLING_FAN_PIN, LOW);
  digitalWrite(WATER_PUMP_PIN, LOW);
  digitalWrite(LED_PLANT_PIN, HIGH);
  digitalWrite(LED_LIGHT_PIN, LOW);
}

// 센서 데이터 읽기 함수
SensorData readSensors()
{
  SensorData data;

  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  data.soilMoisture = analogRead(SOIL_MOISTURE_PIN);
  data.lightLevel = lightMeter.readLightLevel();

  // 센서 데이터값 시리얼 전송
  // 보내는 포맷 - sensor:(TEMP),(SOIL),(HUMID),(LIGHT)
  // 예시 포맷 - sensor:25.5,300,45,1000
  Serial.print("sensor:");
  Serial.print(data.temperature);
  Serial.print(",");
  Serial.print(data.soilMoisture);
  Serial.print(",");
  Serial.print(data.humidity);
  Serial.print(",");
  Serial.println(data.lightLevel);

  return data;
}

// 시리얼 명령 수신 함수
// 아두이노에서 받는 명령어
// 형식- FAN,PUMP,PNT_LED,WHITE_LED,HEAT_PANNEL
// 실제 출력- 255,255,1,0,1
void processSerialCommand(String cmd)
{
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