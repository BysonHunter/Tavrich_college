#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_BMP085 bmp;
Adafruit_SSD1306 display(128, 64, &Wire, -1);
bool sensorOK = false;
bool displayOK = false;
uint32_t lastRead = 0;

void setup() {
  Serial.begin(115200);
  if (!Wire.begin(21, 22, 100000)) return;
  sensorOK = bmp.begin(BMP085_ULTRAHIGHRES, &Wire);
  displayOK = display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  if (!sensorOK) Serial.println("BMP180 not found at 0x77");
  if (!displayOK) Serial.println("OLED unavailable; use Serial output");
}

void loop() {
  if (!sensorOK) { delay(10); return; }
  if (uint32_t(millis() - lastRead) < 2000) return;
  lastRead = millis();
  const float t = bmp.readTemperature();
  const int32_t pressurePa = bmp.readPressure();
  if (!isfinite(t) || pressurePa <= 0) {
    Serial.println("Invalid measurement");
    return;
  }
  const float pressureHpa = pressurePa / 100.0f;
  Serial.printf("T=%.1f C, p=%.1f hPa\n", t, pressureHpa);
  if (displayOK) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("ESP32 + BMP180");
    display.setTextSize(2);
    display.setCursor(0, 18);
    display.print(t, 1); display.println(" C");
    display.setCursor(0, 42);
    display.print(pressureHpa, 0); display.println(" hPa");
    display.display();
  }
}
