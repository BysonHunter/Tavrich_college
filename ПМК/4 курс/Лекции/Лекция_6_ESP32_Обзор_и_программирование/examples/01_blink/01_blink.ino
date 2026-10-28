#include <Arduino.h>
constexpr uint8_t LED_PIN = 23;
bool ledState = false;
uint32_t lastToggle = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void loop() {
  const uint32_t now = millis();
  if (uint32_t(now - lastToggle) >= 500) {
    lastToggle = now;
    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
    Serial.println(ledState ? "LED ON" : "LED OFF");
  }
}
