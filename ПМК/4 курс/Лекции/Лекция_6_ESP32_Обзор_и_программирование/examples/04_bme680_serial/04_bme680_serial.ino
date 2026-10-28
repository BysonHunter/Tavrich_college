#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME680.h>
Adafruit_BME680 bme;
bool ready = false;
uint32_t lastRead = 0;

void setup() {
  Serial.begin(115200);
  if (!Wire.begin(21, 22, 100000)) return;
  ready = bme.begin(0x76);  // Use 0x77 if found by the scanner.
  if (!ready) {
    Serial.println("BME680 not found");
    return;
  }
  bme.setTemperatureOversampling(BME680_OS_8X);
  bme.setHumidityOversampling(BME680_OS_2X);
  bme.setPressureOversampling(BME680_OS_4X);
  bme.setIIRFilterSize(BME680_FILTER_SIZE_3);
  bme.setGasHeater(320, 150);
}

void loop() {
  if (!ready) { delay(10); return; }
  if (uint32_t(millis() - lastRead) < 2000) return;
  lastRead = millis();
  if (!bme.performReading()) {
    Serial.println("Read failed");
    return;
  }
  Serial.printf("T=%.2f C RH=%.1f %% p=%.2f hPa Rgas=%.2f kOhm\n",
      bme.temperature, bme.humidity,
      bme.pressure / 100.0f, bme.gas_resistance / 1000.0f);
}
