class CareFarm {
    public:
        CareFarm();
        void initializeSensors();
        void initializeActuators();
        SensorData readSensors();
        void processSerialCommand(String cmd);
       
        struct SensorData {
            float temperature;
            float humidity;
            int soilMoisture;
            float lightLevel;
        };
};
