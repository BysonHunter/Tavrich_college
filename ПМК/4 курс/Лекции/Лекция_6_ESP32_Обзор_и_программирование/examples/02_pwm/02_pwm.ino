#include <Arduino.h>
constexpr uint8_t LED_PIN = 23;
bool pwmReady = false;

void setup() {
  Serial.begin(115200);
  pwmReady = ledcAttach(LED_PIN, 5000, 8);
  if (!pwmReady) {
    Serial.println("LEDC init failed");
    return;
  }
  ledcWrite(LED_PIN, 128);
}

void loop() {
  delay(10);
}
