// ═══════════════════════════════════════════════════
//  ESP32 Cloud OTA — Secured with API Key
//  
//  Every request to the server includes the API key
//  in the header. Server rejects requests without it.
//
//  GitHub: https://github.com/AnuragShirodkar/esp32-cloud-ota
// ═══════════════════════════════════════════════════

#include <WiFi.h>
#include <HTTPClient.h>
#include <HTTPUpdate.h>
#include <ArduinoOTA.h>
#include <WiFiClientSecure.h>

// ── Wi-Fi Credentials ────────────────────────────
const char* ssid         = "Airtel_m000_6317";
const char* password     = "Air@59781";

// ── ArduinoOTA ───────────────────────────────────
const char* ota_hostname = "Annis-ESP32";
const char* ota_password = "wirelessESP32";

// ── Firmware Version ─────────────────────────────
#define FW_VERSION  "1.0.0"

// ── Cloud Server ─────────────────────────────────
const char* version_url  = "https://esp32-cloud-ota.onrender.com/version";
const char* firmware_url = "https://esp32-cloud-ota.onrender.com/firmware";

// ── API Key ───────────────────────────────────────
//    Must match API_KEY in server.py exactly
const char* api_key = "ESP32-OTA-1ar0922ec";

// ── Update Interval ──────────────────────────────
#define UPDATE_INTERVAL_MS  30000

unsigned long lastUpdateCheck = 0;

// ─────────────────────────────────────────────────
//  Wi-Fi
// ─────────────────────────────────────────────────

void connectWiFi() {
  Serial.printf("\n[WiFi] Connecting to %s\n", ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  uint8_t attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++attempts > 40) {
      Serial.println("\n[WiFi] Failed — restarting...");
      ESP.restart();
    }
  }
  Serial.printf("\n[WiFi] Connected! IP: %s\n",
    WiFi.localIP().toString().c_str());
}

// ─────────────────────────────────────────────────
//  ArduinoOTA
// ─────────────────────────────────────────────────

void setupOTA() {
  ArduinoOTA.setHostname(ota_hostname);
  ArduinoOTA.setPassword(ota_password);
  ArduinoOTA.onStart([]()  { Serial.println("[OTA-IDE] Starting..."); });
  ArduinoOTA.onEnd([]()    { Serial.println("\n[OTA-IDE] Done!"); });
  ArduinoOTA.onProgress([](unsigned int p, unsigned int t) {
    Serial.printf("\r[OTA-IDE] %u%%", (p * 100) / t);
  });
  ArduinoOTA.onError([](ota_error_t e) {
    Serial.printf("[OTA-IDE] Error: %u\n", e);
  });
  ArduinoOTA.begin();
  Serial.println("[OTA-IDE] Listener ready");
}

// ─────────────────────────────────────────────────
//  Fetch Latest Version — sends API key in header
// ─────────────────────────────────────────────────

String getLatestVersion() {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.begin(client, version_url);
  http.addHeader("X-API-Key", api_key);   // ← API key sent here

  int code = http.GET();

  if (code == 200) {
    String payload = http.getString();
    http.end();
    // Parse {"version":"1.0.1"} → "1.0.1"
    int start = payload.indexOf(":\"") + 2;
    int end   = payload.indexOf("\"", start);
    String ver = payload.substring(start, end);
    ver.trim();
    return ver;
  }

  Serial.printf("[HTTP-OTA] Version check failed — HTTP %d\n", code);
  http.end();
  return String("");
}

// ─────────────────────────────────────────────────
//  Download and Flash — sends API key in header
// ─────────────────────────────────────────────────

void doHttpUpdate() {
  Serial.println("[HTTP-OTA] Downloading firmware...");

  WiFiClientSecure client;
  client.setInsecure();

  // Build URL with API key as parameter
  String url = String(firmware_url) + "?key=" + String(api_key);
  httpUpdate.setLedPin(2, LOW);

  httpUpdate.onStart([]() {
    Serial.println("[HTTP-OTA] Flash started");
  });
  httpUpdate.onProgress([](int cur, int total) {
    Serial.printf("\r[HTTP-OTA] %d / %d bytes", cur, total);
  });
  httpUpdate.onEnd([]() {
    Serial.println("\n[HTTP-OTA] Done! Rebooting...");
  });
  httpUpdate.onError([](int err) {
    Serial.printf("\n[HTTP-OTA] Error: %s\n",
      httpUpdate.getLastErrorString().c_str());
  });

 t_httpUpdate_return result =
    httpUpdate.update(client, url);

  switch (result) {
    case HTTP_UPDATE_OK:
      Serial.println("[HTTP-OTA] Update OK — rebooting");
      break;
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("[HTTP-OTA] No update needed");
      break;
    case HTTP_UPDATE_FAILED:
      Serial.println("[HTTP-OTA] Update FAILED");
      break;
  }
}

// ─────────────────────────────────────────────────
//  Version Check
// ─────────────────────────────────────────────────

void checkForUpdate() {
  Serial.printf("[HTTP-OTA] Current: %s — checking server...\n", FW_VERSION);

  String latest = getLatestVersion();

  if (latest.length() == 0) {
    Serial.println("[HTTP-OTA] Server unreachable, skipping");
    return;
  }

  Serial.printf("[HTTP-OTA] Server version: %s\n", latest.c_str());

  if (latest == String(FW_VERSION)) {
    Serial.println("[HTTP-OTA] Already up to date");
    return;
  }

  doHttpUpdate();
}

// ═════════════════════════════════════════════════
//  Setup
// ═════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  pinMode(2, OUTPUT);

  connectWiFi();
  setupOTA();

  Serial.printf("[BOOT] Firmware v%s running\n", FW_VERSION);
  checkForUpdate();
}

// ═════════════════════════════════════════════════
//  Loop
// ═════════════════════════════════════════════════

void loop() {
  ArduinoOTA.handle();

  if (millis() - lastUpdateCheck > UPDATE_INTERVAL_MS) {
    lastUpdateCheck = millis();
    if (WiFi.status() == WL_CONNECTED) {
      checkForUpdate();
    } else {
      Serial.println("[WiFi] Disconnected — reconnecting...");
      WiFi.reconnect();
    }
  }

  // ── Your application code goes here ────────────
}
