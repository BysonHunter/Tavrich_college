#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <math.h>
#include <string.h>

const char* SSID = "YOUR_WIFI_2G4";
const char* PASS = "YOUR_WIFI_PASSWORD";
const char* BROKER = "YOUR_LOCAL_BROKER_IP";
const char* TEMP_TOPIC = "college/room1/temperature";
const char* LED_TOPIC = "college/room1/led/set";
const char* STATUS_TOPIC = "college/room1/status";
WiFiClient network;
PubSubClient mqtt(network);
OneWire wire(4);
DallasTemperature sensors(&wire);
String clientID;
bool present = false, converting = false;
uint32_t requestedAt = 0, lastWiFiTry = 0, lastMqttTry = 0;

void onMessage(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, LED_TOPIC) != 0) return;
  if (length == 2 && memcmp(payload, "ON", 2) == 0) digitalWrite(23, HIGH);
  if (length == 3 && memcmp(payload, "OFF", 3) == 0) digitalWrite(23, LOW);
}

void setup() {
  Serial.begin(115200); pinMode(23, OUTPUT); digitalWrite(23, LOW);
  sensors.begin(); present = sensors.getDeviceCount() > 0;
  sensors.setResolution(12); sensors.setWaitForConversion(false);
  WiFi.mode(WIFI_STA); WiFi.begin(SSID, PASS);
  mqtt.setServer(BROKER, 1883); mqtt.setCallback(onMessage);
  mqtt.setSocketTimeout(2);
  clientID = "esp32-" + String(uint32_t(ESP.getEfuseMac()), HEX);
}

void loop() {
  const uint32_t now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (uint32_t(now - lastWiFiTry) >= 15000) {
      lastWiFiTry = now; WiFi.begin(SSID, PASS);
    }
  } else if (!mqtt.connected() && uint32_t(now - lastMqttTry) >= 5000) {
    lastMqttTry = now;
    if (mqtt.connect(clientID.c_str(), STATUS_TOPIC, 1, true, "offline")) {
      mqtt.publish(STATUS_TOPIC, "online", true);
      mqtt.subscribe(LED_TOPIC);
    }
  }
  if (mqtt.connected()) mqtt.loop();
  if (present && !converting && uint32_t(now - requestedAt) >= 5000) {
    sensors.requestTemperatures(); requestedAt = now; converting = true;
  }
  if (converting && uint32_t(now - requestedAt) >= 750) {
    const float t = sensors.getTempCByIndex(0); converting = false;
    if (t != DEVICE_DISCONNECTED_C && isfinite(t) && mqtt.connected()) {
      char body[80]; snprintf(body, sizeof(body), "{\"temperature_c\":%.2f}", t);
      mqtt.publish(TEMP_TOPIC, body, false);
      Serial.println(body);
    }
  }
  delay(2);
}
