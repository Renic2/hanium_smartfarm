// 센서 핀 정의
#define SOIL_MOISTURE_PIN A0
#define DHT_PIN 2
#define LIGHT_SENSOR_SDA A4
#define LIGHT_SENSOR_SCL A5

// 액추에이터 핀 정의 (MOSFET 연결)
#define THERMAL_PAD_PIN 7
#define COOLING_FAN_PIN 5
#define WATER_PUMP_PIN 6
#define LED_LIGHT_PIN 9
#define LED_PLANT_PIN 10

// 센서 임계값
#define TEMP_MIN 15.0
#define TEMP_MAX 22.0
#define SOIL_MOISTURE_MIN 30
#define SOIL_MOISTURE_MAX 700

// 타이밍 설정
#define PUMP_DURATION 5000
#define SENSOR_DELAY 2000
#define LED_BRIGHTNESS 100

// 라이브러리 포함
#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>

// 센서 객체 생성
DHT dht(DHT_PIN, DHT22);
BH1750 lightMeter;

// 센서 데이터 구조체
struct SensorData {
  float temperature;
  float humidity;
  int soilMoisture;
  int soilMoisturePercent;
  float lightLevel;
};

void setup() {
  Serial.begin(9600);
  dht.begin();
  // 센서 초기화
  initializeSensors();
  
  // 액추에이터 초기화
  initializeActuators();
  
  Serial.println("Smart Farm System Started");
}

void loop() {
  // 센서 데이터 읽기
  SensorData data = readSensors();
  
  // 시리얼 명령 수신 및 처리
  if (Serial.available() > 0) {
  String command = Serial.readStringUntil('\n');
  processSerialCommand(command);
  }
  delay(2000);
}

// 센서 초기화 함수
void initializeSensors() {
  Wire.begin();
  dht.begin();
  
  if (lightMeter.begin()) {
    Serial.println("BH1750 initialized successfully");
  } else {
    Serial.println("BH1750 initialization failed");
  }
}

// 액추에이터 초기화 함수
void initializeActuators() {
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
  analogWrite(LED_LIGHT_PIN, LED_BRIGHTNESS);
}

// 센서 데이터 읽기 함수
SensorData readSensors() {
  SensorData data;
  
  data.temperature = dht.readTemperature();
  data.humidity = dht.readHumidity();
  data.soilMoisture = analogRead(SOIL_MOISTURE_PIN);
  data.soilMoisturePercent = map(data.soilMoisture, 0, SOIL_MOISTURE_MAX, 0, 100);
  data.lightLevel = lightMeter.readLightLevel();

  Serial.print("TEMP:"); Serial.print(data.temperature);
  Serial.print(",HUM:"); Serial.print(data.humidity);
  Serial.print(",LIGHT:"); Serial.print(data.lightLevel);
  Serial.print(",SOIL:"); Serial.println(data.soilMoisture);


  return data;
}

// 시리얼 명령 수신 함수

void processSerialCommand(String cmd) {
  cmd.trim();

  if (cmd.startsWith("PUMP:")) {
    if (cmd.endsWith("ON")) {
      digitalWrite(WATER_PUMP_PIN, HIGH);
    } else if (cmd.endsWith("OFF")) {
      digitalWrite(WATER_PUMP_PIN, LOW);
    }
  } else if (cmd.startsWith("FAN:")) {
    if (cmd.endsWith("ON")) {
      digitalWrite(COOLING_FAN_PIN, HIGH);
    } else if (cmd.endsWith("OFF")) {
      digitalWrite(COOLING_FAN_PIN, LOW);
    }
  } else if (cmd.startsWith("HEAT_PANNEL:") || cmd.startsWith("HEAT PANNEL:")) {
    if (cmd.endsWith("ON")) {
      digitalWrite(THERMAL_PAD_PIN, HIGH);
    } else if (cmd.endsWith("OFF")) {
      digitalWrite(THERMAL_PAD_PIN, LOW);
    }
  } else if (cmd.startsWith("LED1:") || cmd.startsWith("LED1: ")) {
    if (cmd.endsWith("ON")) {
      digitalWrite(LED_PLANT_PIN, HIGH);
    } else if (cmd.endsWith("OFF")) {
      digitalWrite(LED_PLANT_PIN, LOW);
    }
  } else if (cmd.startsWith("LED2:") || cmd.startsWith("LED2: ")) {
    if (cmd.endsWith("ON")) {
      digitalWrite(LED_LIGHT_PIN, HIGH);
    } else if (cmd.endsWith("OFF")) {
      digitalWrite(LED_LIGHT_PIN, LOW);}
  } 