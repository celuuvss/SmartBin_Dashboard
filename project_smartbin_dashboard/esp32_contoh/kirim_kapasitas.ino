/*
  kirim_kapasitas.ino
  Contoh sketch ESP32 untuk membaca sensor ultrasonik (HC-SR04) di 3 tempat
  sampah (Organik, Anorganik, Residu), menghitung persentase kapasitas,
  lalu mengirimkannya via HTTP POST (WiFi) ke server Flask dashboard.

  Rangkaian (contoh, sesuaikan dengan pin ESP32 kamu):
    Sensor Organik   -> TRIG: 5,  ECHO: 18
    Sensor Anorganik -> TRIG: 19, ECHO: 21
    Sensor Residu    -> TRIG: 22, ECHO: 23

  Library yang dibutuhkan (install via Arduino Library Manager):
    - WiFi.h        (built-in ESP32 core)
    - HTTPClient.h  (built-in ESP32 core)
    - ArduinoJson   (by Benoit Blanchon)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ---------- KONFIGURASI ----------
const char* WIFI_SSID     = "NAMA_WIFI_ANDA";
const char* WIFI_PASSWORD = "PASSWORD_WIFI_ANDA";

// Ganti dengan alamat IP komputer yang menjalankan app.py (Flask), contoh: 192.168.1.10
const char* SERVER_URL = "http://192.168.1.10:5000/api/kapasitas";

// Tinggi bin dalam cm (jarak sensor ke dasar tempat sampah saat kosong)
const float TINGGI_BIN_CM = 40.0;

// Pin sensor ultrasonik tiap bin
const int TRIG_ORGANIK = 5,  ECHO_ORGANIK = 18;
const int TRIG_ANORGANIK = 19, ECHO_ANORGANIK = 21;
const int TRIG_RESIDU = 22, ECHO_RESIDU = 23;

const unsigned long INTERVAL_KIRIM_MS = 60000; // kirim data tiap 60 detik
unsigned long waktuTerakhirKirim = 0;


void setup() {
  Serial.begin(115200);

  pinMode(TRIG_ORGANIK, OUTPUT);   pinMode(ECHO_ORGANIK, INPUT);
  pinMode(TRIG_ANORGANIK, OUTPUT); pinMode(ECHO_ANORGANIK, INPUT);
  pinMode(TRIG_RESIDU, OUTPUT);    pinMode(ECHO_RESIDU, INPUT);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Menghubungkan ke WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi terhubung. IP ESP32: " + WiFi.localIP().toString());
}


// Membaca jarak sensor ultrasonik (cm)
float bacaJarakCM(int pinTrig, int pinEcho) {
  digitalWrite(pinTrig, LOW);
  delayMicroseconds(2);
  digitalWrite(pinTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinTrig, LOW);

  long durasi = pulseIn(pinEcho, HIGH, 30000); // timeout 30ms
  if (durasi == 0) return TINGGI_BIN_CM;        // gagal baca, anggap kosong
  return durasi * 0.0343 / 2.0;                 // konversi ke cm
}

// Mengubah jarak sensor menjadi persentase kapasitas terisi
int hitungPersenKapasitas(float jarakCM) {
  float terisi = TINGGI_BIN_CM - jarakCM;
  if (terisi < 0) terisi = 0;
  if (terisi > TINGGI_BIN_CM) terisi = TINGGI_BIN_CM;
  return (int)((terisi / TINGGI_BIN_CM) * 100);
}

void kirimDataKapasitas(int organik, int anorganik, int residu) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi tidak terhubung, data tidak dikirim.");
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<128> doc;
  doc["organik"] = organik;
  doc["anorganik"] = anorganik;
  doc["residu"] = residu;

  String bodyJson;
  serializeJson(doc, bodyJson);

  int kodeRespon = http.POST(bodyJson);
  Serial.print("Kirim data -> kode respon: ");
  Serial.println(kodeRespon);

  http.end();
}

void loop() {
  if (millis() - waktuTerakhirKirim >= INTERVAL_KIRIM_MS) {
    int persenOrganik   = hitungPersenKapasitas(bacaJarakCM(TRIG_ORGANIK, ECHO_ORGANIK));
    int persenAnorganik = hitungPersenKapasitas(bacaJarakCM(TRIG_ANORGANIK, ECHO_ANORGANIK));
    int persenResidu    = hitungPersenKapasitas(bacaJarakCM(TRIG_RESIDU, ECHO_RESIDU));

    Serial.printf("Organik: %d%% | Anorganik: %d%% | Residu: %d%%\n",
                  persenOrganik, persenAnorganik, persenResidu);

    kirimDataKapasitas(persenOrganik, persenAnorganik, persenResidu);
    waktuTerakhirKirim = millis();
  }
}
