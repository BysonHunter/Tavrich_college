#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Adafruit_BME680.h>
#include <math.h>

const char* SSID = "YOUR_WIFI_2G4";
const char* PASS = "YOUR_WIFI_PASSWORD";
Adafruit_BME680 bme;
WebServer server(80);
bool sensorReady = false;
bool valid = false;
uint32_t lastTry = 0;
uint32_t measuredAt = 0;
float temperatureC = NAN;

void sampleTemperature() {
  if (!sensorReady || !bme.performReading()) {
    valid = false;
    return;
  }
  temperatureC = bme.temperature;
  valid = isfinite(temperatureC);
  if (valid) measuredAt = millis();
}

void sendTemperature() {
  server.sendHeader("Cache-Control", "no-store");
  const uint32_t age = uint32_t(millis() - measuredAt);
  if (!valid || age > 5000) {
    server.send(503, "application/json", "{\"error\":\"sensor_unavailable\"}");
    return;
  }
  char body[128];
  snprintf(body, sizeof(body),
      "{\"temperature_c\":%.2f,\"age_ms\":%lu}",
      temperatureC, static_cast<unsigned long>(age));
  server.send(200, "application/json", body);
}

void setup() {
  Serial.begin(115200);
  if (Wire.begin(21, 22, 100000)) {
    sensorReady = bme.begin(0x76); // Change to 0x77 if required.
  }
  if (sensorReady) {
    bme.setTemperatureOversampling(BME680_OS_8X);
    bme.setHumidityOversampling(BME680_OS_2X);
    bme.setPressureOversampling(BME680_OS_4X);
    bme.setGasHeater(320, 150);
    sampleTemperature();
  } else {
    Serial.println("BME680 not found; API will return HTTP 503");
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID, PASS);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED &&
         uint32_t(millis() - started) < 15000) {
    delay(100);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi timeout: check SSID, password and 2.4 GHz");
    return;
  }
  Serial.print("Open http://");
  Serial.print(WiFi.localIP());
  Serial.println("/");
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html; charset=utf-8",
      "<!doctype html><meta charset='utf-8'>"
      "<title>ESP32 temperature</title><h1>ESP32 + BME680</h1>"
      "<p id='t'>Waiting for sensor...</p>"
      "<script>async function update(){try{"
      "const r=await fetch('/api/temperature',{cache:'no-store'});"
      "if(!r.ok)throw new Error('HTTP '+r.status);"
      "const d=await r.json();document.getElementById('t').textContent="
      "d.temperature_c.toFixed(2)+' C, age '+d.age_ms+' ms';"
      "}catch(e){document.getElementById('t').textContent='Sensor unavailable';}}"
      "update();setInterval(update,2000);</script>");
  });
  server.on("/api/temperature", HTTP_GET, sendTemperature);
  server.onNotFound([]() { server.send(404, "text/plain", "Not found"); });
  server.begin();
  lastTry = millis();
}

void loop() {
  server.handleClient();
  if (sensorReady && uint32_t(millis() - lastTry) >= 2000) {
    lastTry = millis();
    sampleTemperature(); // Blocking sample; brief HTTP pause is possible.
  }
  delay(2);
}
