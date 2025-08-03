#include "CareFarm.h"

CareFarm carefarm();

void setup()
{
    Serial.begin(9600);             // 시리얼 통신 시작
    carefarm.initializeSensors();   // 센서 초기화
    carefarm.initializeActuators(); // 액추에이터 초기화
}

void loop()
{
    real_time = millis(); // 현재 시간 기록
    if (real_time - last_read_time >= 2000) // 2초마다 센서 데이터 읽기
    {                                             
        SensorData data = carefarm.readSensors();
    }

    // 시리얼 명령 수신 및 처리
    if (Serial.available() > 0)
    {
        String cmd = Serial.readStringUntil('\n');
        carefarm.processSerialCommand(cmd);
    }
}
