#include <Wire.h>

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

// 센서 데이터 구조체
struct SensorData {
  float temperature = 25.0;
  float humidity = 50.0;
  int soilMoisture = 300;
  int soilMoisturePercent = 50;
  float lightLevel = 100.0;
};

struct ActuatorData{
    int thermalPadState = 0;
    int coolingFanState = 0;
    int waterPumpState = 0;
    int ledLightState = 0;
    int ledPlantState = 0;
};


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
  digitalWrite(LED_PLANT_PIN, LOW);
  analogWrite(LED_LIGHT_PIN, LED_BRIGHTNESS);
  digitalWrite(LED_LIGHT_PIN, LOW);
}

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
}

void setup() {
  Serial.begin(9600);
  dht.begin();

  // 액추에이터 초기화
  initializeActuators();
  
  Serial.println("Smart Farm System Started");

  delay(3000); // 초기화 대기 시간
}

void loop() {
  // 시리얼 명령 수신 및 처리
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processSerialCommand(command);

    // 액추에이터 상태 출력
    String fanState = digitalRead(COOLING_FAN_PIN) ? "ON" : "OFF";
    String pumpState = digitalRead(WATER_PUMP_PIN) ? "ON" : "OFF";
    String heatPadState = digitalRead(THERMAL_PAD_PIN) ? "ON" : "OFF";
    String led1State = digitalRead(LED_PLANT_PIN) ? "ON" : "OFF";
    String led2State = digitalRead(LED_LIGHT_PIN) ? "ON" : "OFF";

    Serial.print("[ACTUATOR STATE] ");
    Serial.print("FAN: "); Serial.print(fanState); Serial.print(", ");
    Serial.print("PUMP: "); Serial.print(pumpState); Serial.print(", ");
    Serial.print("HEAT_PANNEL: "); Serial.print(heatPadState); Serial.print(", ");
    Serial.print("LED_PLANT: "); Serial.print(led1State); Serial.print(", ");
    Serial.print("LED_WHITE: "); Serial.println(led2State);
  }

  delay(2000);
}
