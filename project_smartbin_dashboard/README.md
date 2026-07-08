# SmartBin Dashboard

Dashboard monitoring untuk sistem **SmartBin** (Smart Waste Management),
dibuat mengikuti desain yang diberikan. Frontend berbasis **Flask (Python)
+ HTML/CSS/JS**, siap menerima data dari **Arduino/ESP32** via WiFi (HTTP REST).

## Struktur Proyek

```
smartbin_dashboard/
├── app.py                     # Backend Flask (routes + API)
├── database.py                # Helper SQLite (simpan histori data)
├── requirements.txt
├── data/                      # Otomatis dibuat, berisi smartbin.db
├── templates/
│   └── index.html             # Halaman dashboard
├── static/
│   ├── css/style.css
│   └── js/dashboard.js        # Polling data + render chart & tabel
└── esp32_contoh/
    └── kirim_kapasitas.ino    # Contoh sketch Arduino/ESP32
```

## 1. Menjalankan Dashboard (di komputer/laptop/Raspberry Pi)

```bash
cd smartbin_dashboard
pip install -r requirements.txt
python app.py
```

Buka browser ke `http://localhost:5000` (atau `http://IP_KOMPUTER:5000`
dari perangkat lain di jaringan WiFi yang sama).

Server otomatis membuat database `data/smartbin.db` saat pertama dijalankan.

> Catatan: `app.py` menjalankan `host="0.0.0.0"` supaya ESP32 di jaringan
> WiFi yang sama bisa mengirim data ke server ini. Pastikan komputer dan
> ESP32 terhubung ke WiFi/router yang sama, dan cari IP komputer dengan
> `ipconfig` (Windows) atau `ifconfig` / `ip addr` (Linux/Mac).

## 2. Integrasi dengan Arduino/ESP32 (Backend IoT)

Karena backend IoT kamu pakai Arduino, cara paling praktis untuk kirim data
ke dashboard Python adalah lewat **ESP32/ESP8266 sebagai jembatan WiFi**
(Arduino Uno/Mega biasa tidak punya WiFi built-in, jadi kalau board kamu
Arduino Uno, tambahkan modul ESP8266 sebagai WiFi shield, atau langsung
gunakan ESP32 yang sudah include WiFi).

Contoh sketch ada di `esp32_contoh/kirim_kapasitas.ino`. Sketch ini:
1. Membaca sensor ultrasonik (HC-SR04) di 3 tempat sampah.
2. Menghitung persentase kapasitas terisi.
3. Mengirim data via `HTTP POST` ke endpoint dashboard.

### Endpoint API yang tersedia

| Endpoint | Method | Dipanggil oleh | Fungsi |
|---|---|---|---|
| `/api/kapasitas` | POST | ESP32 (sensor ultrasonik) | Kirim data kapasitas 3 bin |
| `/api/klasifikasi` | POST | Modul kamera/ML (ESP32-CAM dll) | Kirim hasil klasifikasi sampah |
| `/api/dashboard-data` | GET | Browser (dashboard.js) | Data gabungan untuk ditampilkan |

**Contoh body JSON `/api/kapasitas`:**
```json
{
  "organik": 75,
  "anorganik": 40,
  "residu": 20
}
```

**Contoh body JSON `/api/klasifikasi`:**
```json
{
  "nama_objek": "Kulit Pisang",
  "jenis": "Organik",
  "confidence": 98.7,
  "gambar_url": "http://192.168.1.20/foto/123.jpg"
}
```

Kamu bisa test endpoint ini tanpa Arduino dulu pakai `curl`:
```bash
curl -X POST http://localhost:5000/api/kapasitas \
  -H "Content-Type: application/json" \
  -d '{"organik": 75, "anorganik": 40, "residu": 20}'
```

## 3. Kalau Backend Arduino-nya Bukan ESP32 (Serial USB)

Jika modul WiFi tidak dipakai dan Arduino terhubung via kabel USB (Serial)
ke komputer yang menjalankan Flask, kamu perlu skrip Python tambahan yang:
1. Membaca data dari Serial port (pakai library `pyserial`).
2. Mem-forward data itu ke fungsi `db.simpan_kapasitas()` langsung
   (tanpa lewat HTTP), atau memanggil endpoint `/api/kapasitas` secara lokal.

Beri tahu saya kalau kamu ingin saya buatkan skrip jembatan Serial→Flask ini
juga — modelnya akan mirip, hanya sumber datanya beda (Serial, bukan WiFi).

## 4. Kustomisasi

- **Ambang batas status** (Aman/Sedang/Penuh) diatur di `app.py`,
  variabel `BATAS_PENUH` dan `BATAS_SEDANG`.
- **Tinggi bin untuk kalkulasi %** diatur di sketch `.ino`,
  variabel `TINGGI_BIN_CM`.
- **Interval polling dashboard** diatur di `static/js/dashboard.js`,
  variabel `POLL_INTERVAL_MS` (default 5 detik).
- **Menu sidebar, warna, dsb** ada di `templates/index.html` dan
  `static/css/style.css` — sudah dibuat semirip mungkin dengan desain
  yang diberikan (kartu Organik/Anorganik/Residu, grafik, status
  real-time, riwayat klasifikasi, notifikasi).

## 5. Yang Masih Perlu Dilengkapi Sesuai Kebutuhan Proyekmu

- Fitur klasifikasi gambar sampah (Organik/Anorganik) belum termasuk
  model ML-nya — endpoint `/api/klasifikasi` sudah siap menerima hasil
  klasifikasi dari model kamu (baik dijalankan di ESP32-CAM, Raspberry
  Pi, atau server Python terpisah).
- Halaman selain Dashboard (Tempat Sampah, Pengaturan, Pengguna, dll)
  di sidebar baru berupa link kosong — beri tahu saya kalau perlu
  dibuatkan halamannya juga.
- Autentikasi/login belum ada, mengingat gambar hanya menunjukkan
  dashboard utama.
