"""
app.py
Backend Flask untuk Dashboard SmartBin.

Alur data:
1. Arduino/ESP32 (dengan sensor ultrasonik di tiap bin) terhubung WiFi,
   lalu mengirim data kapasitas via HTTP POST ke endpoint /api/kapasitas.
2. Modul klasifikasi (mis. ESP32-CAM + model ML, atau server ML terpisah)
   mengirim hasil klasifikasi via HTTP POST ke endpoint /api/klasifikasi.
3. Browser (dashboard) polling endpoint /api/dashboard-data setiap
   beberapa detik untuk menampilkan data terbaru secara "real-time".

Jalankan:
    pip install flask
    python app.py
Lalu buka http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from datetime import datetime
import database as db

app = Flask(__name__)

# Batas ambang untuk status kapasitas & notifikasi otomatis
BATAS_PENUH = 80   # >= ini dianggap "Penuh" / perlu pengangkutan
BATAS_SEDANG = 50  # >= ini dianggap "Sedang"



def status_dari_persen(persen):
    if persen >= BATAS_PENUH:
        return "Penuh"
    elif persen >= BATAS_SEDANG:
        return "Sedang"
    return "Aman"


# ---------------------------------------------------------------------------
# HALAMAN DASHBOARD
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API UNTUK ESP32 / ARDUINO (backend IoT) -> KIRIM DATA KE SINI
# ---------------------------------------------------------------------------

@app.route("/api/kapasitas", methods=["POST"])
def terima_kapasitas():
    """
    Endpoint yang dipanggil ESP32 untuk mengirim data kapasitas sensor.

    Contoh payload JSON dari Arduino:
    {
        "organik": 75,
        "anorganik": 40,
        "residu": 20
    }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "Payload JSON tidak valid"}), 400

    try:
        organik = int(payload["organik"])
        anorganik = int(payload["anorganik"])
        residu = int(payload["residu"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"status": "error", "message": "Field organik/anorganik/residu wajib diisi angka"}), 400

    db.simpan_kapasitas(organik, anorganik, residu)

    # Buat notifikasi otomatis kalau ada bin yang penuh
    for nama, nilai in [("Organik", organik), ("Anorganik", anorganik), ("Residu", residu)]:
        if nilai >= BATAS_PENUH:
            db.buat_notifikasi(
                "warning",
                f"Kapasitas {nama} Hampir Penuh",
                f"Kapasitas sampah {nama.lower()} sudah {nilai}%. Segera lakukan pengangkutan."
            )

    return jsonify({"status": "ok", "message": "Data kapasitas tersimpan"}), 201


@app.route("/api/klasifikasi", methods=["POST"])
def terima_klasifikasi():
    """
    Endpoint yang dipanggil modul klasifikasi (mis. ESP32-CAM + ML) untuk
    mengirim hasil klasifikasi sampah terbaru.

    Contoh payload JSON:
    {
        "nama_objek": "Kulit Pisang",
        "jenis": "Organik",
        "confidence": 98.7,
        "gambar_url": "http://.../foto123.jpg"   # opsional
    }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "Payload JSON tidak valid"}), 400

    try:
        nama_objek = str(payload["nama_objek"])
        jenis = str(payload["jenis"])
        confidence = float(payload["confidence"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"status": "error", "message": "Field nama_objek/jenis/confidence wajib diisi"}), 400

    gambar_url = payload.get("gambar_url")

    db.simpan_klasifikasi(nama_objek, jenis, confidence, gambar_url)
    db.buat_notifikasi(
        "success",
        f"Objek Baru Terklasifikasi: {jenis}",
        f"{nama_objek} berhasil diklasifikasikan sebagai {jenis} ({confidence:.1f}% yakin)."
    )

    return jsonify({"status": "ok", "message": "Klasifikasi tersimpan"}), 201


# ---------------------------------------------------------------------------
# API UNTUK FRONTEND (dashboard) -> DIPANGGIL OLEH dashboard.js
# ---------------------------------------------------------------------------

@app.route("/api/dashboard-data")
def dashboard_data():
    """Data gabungan yang dipoll browser tiap beberapa detik."""
    terbaru = db.ambil_kapasitas_terbaru()
    if terbaru is None:
        # Data default kalau ESP32 belum pernah mengirim apapun
        terbaru = {"organik": 0, "anorganik": 0, "residu": 0, "waktu": "-"}

    organik = terbaru["organik"]
    anorganik = terbaru["anorganik"]
    residu = terbaru["residu"]
    rata2 = round((organik + anorganik + residu) / 3)

    history = db.ambil_kapasitas_history(limit=24)
    klasifikasi = db.ambil_klasifikasi_terbaru(limit=6)
    notifikasi = db.ambil_notifikasi_terbaru(limit=6)

    return jsonify({
        "kapasitas": {
            "organik": {"persen": organik, "status": status_dari_persen(organik)},
            "anorganik": {"persen": anorganik, "status": status_dari_persen(anorganik)},
            "residu": {"persen": residu, "status": status_dari_persen(residu)},
            "rata2": {"persen": rata2, "status": status_dari_persen(rata2)},
        },
        "grafik": {
            "waktu": [h["waktu"][-8:-3] for h in history],  # ambil jam:menit saja
            "organik": [h["organik"] for h in history],
            "anorganik": [h["anorganik"] for h in history],
            "residu": [h["residu"] for h in history],
        },
        "klasifikasi": klasifikasi,
        "notifikasi": notifikasi,
        "waktu_update": datetime.now().strftime("%H:%M:%S"),
    })


if __name__ == "__main__":
    db.init_db()
    # host="0.0.0.0" agar ESP32 di jaringan WiFi yang sama bisa mengakses server ini
    app.run(host="0.0.0.0", port=5000, debug=True)
