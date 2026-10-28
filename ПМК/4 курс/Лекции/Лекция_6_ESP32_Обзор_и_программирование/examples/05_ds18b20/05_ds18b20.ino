#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
OneWire oneWire(4);
DallasTemperature sensors(&oneWire);

void setup() {
  Serial.begin(115200);
  sensors.begin();
  sensors.setResolution(12);
}

void loop() {
  sensors.requestTemperatures(); // Waits for conversion by default.
  const float t = sensors.getTempCByIndex(0);
  if (t == DEVICE_DISCONNECTED_C) {
    Serial.println("Sensor disconnected");
  } else {
    Serial.printf("T=%.2f C\n", t);
  }
  delay(1000);
}
