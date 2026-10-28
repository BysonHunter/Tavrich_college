#include <Arduino.h>
#include <Wire.h>

void setup() {
  Serial.begin(115200);
  if (!Wire.begin(21, 22, 100000)) {
    Serial.println("I2C init failed");
    return;
  }
  for (uint8_t addr = 0x08; addr <= 0x77; ++addr) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.printf("Found 0x%02X\n", addr);
    }
  }
  Serial.println("Scan complete");
}

void loop() { delay(10); }
