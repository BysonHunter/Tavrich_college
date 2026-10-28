#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <math.h>

const char* SSID = "YOUR_WIFI_2G4";
const char* PASS = "YOUR_WIFI_PASSWORD";
OneWire wire(4);
DallasTemperature sensors(&wire);
WebServer server(80);
bool sensorPresent = false, valid = false, serverStarted = false;
bool converting = false;
uint32_t requestedAt = 0, measuredAt = 0;
float temperatureC = NAN;

void serviceSensor() {
  if (!sensorPresent) return;
  if (converting && uint32_t(millis() - requestedAt) >= 750) {
    temperatureC = sensors.getTempCByIndex(0);
    valid = temperatureC != DEVICE_DISCONNECTED_C && isfinite(temperatureC);
    if (valid) measuredAt = millis();
    converting = false;
  }
  if (!converting && uint32_t(millis() - requestedAt) >= 2000) {
    sensors.requestTemperatures();
    requestedAt = millis();
    converting = true;
  }
}

void setup() {
  Serial.begin(115200);
  sensors.begin();
  sensorPresent = sensors.getDeviceCount() > 0;
  sensors.setResolution(12);
  sensors.setWaitForConversion(false);
  if (sensorPresent) {
    sensors.requestTemperatures(); requestedAt = millis(); converting = true;
  }
  WiFi.mode(WIFI_STA); WiFi.begin(SSID, PASS);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && uint32_t(millis() - start) < 15000) {
    serviceSensor(); delay(10);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi timeout"); return;
  }
  Serial.print("Open http://"); Serial.println(WiFi.localIP());
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html; charset=utf-8",
      "<!doctype html><meta charset='utf-8'><title>DS18B20</title>"
      "<h1>ESP32 + DS18B20</h1><p id='t'>Waiting...</p>"
      "<script>async function update(){try{const r=await fetch('/temperature');"
      "if(!r.ok)throw 1;const d=await r.json();"
      "document.getElementById('t').textContent=d.c.toFixed(2)+' C';"
      "}catch(e){document.getElementById('t').textContent='Sensor unavailable';}}"
      "update();setInterval(update,2000);</script>");
  });
  server.on("/temperature", HTTP_GET, []() {
    server.sendHeader("Cache-Control", "no-store");
    if (!valid || uint32_t(millis() - measuredAt) > 5000) {
      server.send(503, "application/json", "{\"error\":\"no_measurement\"}"); return;
    }
    char text[64]; snprintf(text, sizeof(text), "{\"c\":%.2f}", temperatureC);
    server.send(200, "application/json", text);
  });
  server.begin(); serverStarted = true;
}

void loop() {
  serviceSensor();
  if (serverStarted) server.handleClient();
  delay(2);
}
