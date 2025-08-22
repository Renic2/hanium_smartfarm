/**
 * Hanium 스마트팜 - 최종 테스트용 펌웨어 (Heartbeat 추가)
 * * 기능:
 * 1. 센서값 측정 및 시리얼 출력 (2초 간격)
 * 2. 액추에이터 제어 명령 수신 및 실행
 * 3. Heartbeat 신호 전송 (5초 간격)
 * * 핀 변경사항:
 * - D4: 백색등 (WHITE_LED)
 * - D5: 워터 펌프 (WATER_PUMP)
 */

// =================================================================
// 1. 라이브러리 및 설정
// =================================================================

#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>

// --- 센서 핀 정의 ---
#define DHT_PIN 2
#define SOIL_PIN A0

// --- 액추에이터 핀 정의 ---
#define FAN_PIN 3
#define WHITE_LED_PIN 4
#define WATER_PUMP_PIN 5
#define GROW_LIGHT_PIN 6
#define HEAT_PANNEL_PIN 7

// --- 센서 객체 생성 ---
DHT dht(DHT_PIN, DHT22);
BH1750 lightMeter;

// --- 타이머 변수 ---
unsigned long lastSensorReadTime = 0;
unsigned long lastHeartbeatTime = 0; // Heartbeat 타이머 추가
const long sensorInterval = 2000;    // 2초
const long heartbeatInterval = 5000; // 5초

// =================================================================
// 2. 초기 설정 (setup)
// =================================================================
void setup() {
  Serial.begin(9600);

  dht.begin();
  Wire.begin();
  lightMeter.begin();

  pinMode(FAN_PIN, OUTPUT);
  pinMode(WATER_PUMP_PIN, OUTPUT);
  pinMode(WHITE_LED_PIN, OUTPUT);
  pinMode(GROW_LIGHT_PIN, OUTPUT);
  pinMode(HEAT_PANNEL_PIN, OUTPUT);

  digitalWrite(WHITE_LED_PIN, LOW);
  digitalWrite(HEAT_PANNEL_PIN, LOW);
  analogWrite(FAN_PIN, 0);
  analogWrite(WATER_PUMP_PIN, 0);
  analogWrite(GROW_LIGHT_PIN, 0);

  Serial.println("Arduino Test Ready (with Heartbeat).");
}

// =================================================================
// 3. 메인 루프 (loop)
// =================================================================
void loop() {
  unsigned long currentTime = millis(); // 현재 시간을 한 번만 읽어옴

  // 2초마다 센서 값 전송
  if (currentTime - lastSensorReadTime >= sensorInterval) {
    readAndSendSensors();
    lastSensorReadTime = currentTime;
  }

  // ★★★★★ Heartbeat 기능 추가 ★★★★★
  // 5초마다 Heartbeat 신호 전송
  if (currentTime - lastHeartbeatTime >= heartbeatInterval) {
    sendHeartbeat();
    lastHeartbeatTime = currentTime;
  }

  // 시리얼 명령 수신
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
}

// =================================================================
// 4. 기능별 함수
// =================================================================

/**
 * @brief "HEARTBEAT:OK" 메시지를 시리얼로 전송합니다.
 */
void sendHeartbeat() {
  Serial.println("HEARTBEAT:");
}

void readAndSendSensors() {
  float temp = dht.readTemperature();
  float humid = dht.readHumidity();
  int soil = analogRead(SOIL_PIN);
  float light = lightMeter.readLightLevel();

  if (isnan(temp) || isnan(humid)) {
    return; // 센서 읽기 실패 시 전송 안 함
  }

  Serial.print("SENSOR:");
  Serial.print(temp);
  Serial.print(",");
  Serial.print(soil);
  Serial.print(",");
  Serial.print(humid);
  Serial.print(",");
  Serial.println(light);
}

void processCommand(String cmd) {
  cmd.trim();

  char buf[32];
  cmd.toCharArray(buf, sizeof(buf));

  char* token;
  int index = 0;

  token = strtok(buf, ",");
  while (token != NULL) {
    int value = atoi(token);

    switch (index) {
      case 0: analogWrite(FAN_PIN, value); break;
      case 1: analogWrite(WATER_PUMP_PIN, value); break;
      case 2: digitalWrite(HEAT_PANNEL_PIN, value > 0 ? HIGH : LOW); break;
      case 3: analogWrite(GROW_LIGHT_PIN, value > 0 ? 255 : 0); break;
      case 4: digitalWrite(WHITE_LED_PIN, value > 0 ? HIGH : LOW); break;
    }
    token = strtok(NULL, ",");
    index++;
  }
}