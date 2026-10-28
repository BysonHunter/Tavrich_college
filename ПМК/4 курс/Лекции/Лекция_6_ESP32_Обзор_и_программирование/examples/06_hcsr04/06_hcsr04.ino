#include <Arduino.h>
constexpr uint8_t TRIG_PIN = 18;
constexpr uint8_t ECHO_PIN = 19;

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);
}

void loop() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  const unsigned long us = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (us == 0) {
    Serial.println("No echo: timeout");
  } else {
    const float cm = us * 0.0343f / 2.0f;
    Serial.printf("Distance=%.1f cm\n", cm);
  }
  delay(100);
}
