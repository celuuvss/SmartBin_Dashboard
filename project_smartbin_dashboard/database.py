"""
database.py
Modul helper untuk menyimpan & mengambil data SmartBin menggunakan SQLite.
Semua data dari Arduino/ESP32 (kapasitas sensor) dan hasil klasifikasi
(dari kamera/ML) disimpan di sini agar bisa ditampilkan di dashboard
dan tetap ada walau server Flask di-restart.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "smartbin.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Membuat tabel jika belum ada. Dipanggil sekali saat app.py start."""
    conn = get_conn()
    cur = conn.cursor()

    # Riwayat kapasitas tiap jenis sampah (dikirim ESP32 tiap beberapa menit)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kapasitas_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT NOT NULL,
            organik INTEGER NOT NULL,
            anorganik INTEGER NOT NULL,
            residu INTEGER NOT NULL
        )
    """)

    # Riwayat klasifikasi sampah (dikirim modul kamera/ML, mis. ESP32-CAM)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS klasifikasi_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT NOT NULL,
            nama_objek TEXT NOT NULL,
            jenis TEXT NOT NULL,
            confidence REAL NOT NULL,
            gambar_url TEXT
        )
    """)

    # Notifikasi sistem (otomatis dibuat oleh backend saat kondisi tertentu)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifikasi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT NOT NULL,
            tipe TEXT NOT NULL,          -- warning | info | success
            judul TEXT NOT NULL,
            pesan TEXT NOT NULL,
            dibaca INTEGER DEFAULT 0
        )
    """)

    # Seed data if database is brand new
    cur.execute("SELECT COUNT(*) FROM kapasitas_log")
    if cur.fetchone()[0] == 0:
        from datetime import timedelta
        base_time = datetime.now()
        
        # Seed Kapasitas
        kapasitas_seed = [
            (11, 77, 50, 25),
            (10, 75, 48, 23),
            (9, 68, 38, 18),
            (8, 63, 40, 20),
            (7, 70, 42, 17),
            (6, 78, 45, 15),
            (5, 78, 50, 12),
            (4, 80, 48, 14),
            (3, 82, 45, 18),
            (2, 80, 42, 22),
            (1, 78, 45, 23),
            (0, 75, 40, 20)
        ]
        for diff_hours, org, anorg, res in kapasitas_seed:
            t = (base_time - timedelta(hours=diff_hours)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO kapasitas_log (waktu, organik, anorganik, residu) VALUES (?, ?, ?, ?)", (t, org, anorg, res))
            
        # Seed Klasifikasi
        klasifikasi_seed = [
            (10, "Sisa Makanan", "Organik", 97.2),
            (8, "Sedotan Plastik", "Anorganik", 91.4),
            (6, "Kertas", "Anorganik", 93.1),
            (4, "Botol Plastik", "Anorganik", 96.3),
            (2, "Kulit Pisang", "Organik", 98.7)
        ]
        for diff_minutes, nama, jenis, conf in klasifikasi_seed:
            t = (base_time - timedelta(minutes=diff_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO klasifikasi_log (waktu, nama_objek, jenis, confidence, gambar_url) VALUES (?, ?, ?, ?, ?)", (t, nama, jenis, conf, ""))
            
        # Seed Notifikasi
        notif_seed = [
            (12, "info", "Data berhasil diperbarui", "Data kapasitas telah diperbarui"),
            (7, "success", "Sistem Berjalan Normal", "Semua sistem berfungsi dengan baik"),
            (4, "info", "Sampah Anorganik Aman", "Kapasitas dalam kondisi aman"),
            (2, "warning", "Kapasitas Organik Hampir Penuh", "Harap segera lakukan pengangkutan")
        ]
        for diff_minutes, tipe, judul, pesan in notif_seed:
            t = (base_time - timedelta(minutes=diff_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO notifikasi (waktu, tipe, judul, pesan) VALUES (?, ?, ?, ?)", (t, tipe, judul, pesan))

    conn.commit()
    conn.close()


def simpan_kapasitas(organik, anorganik, residu):
    conn = get_conn()
    conn.execute(
        "INSERT INTO kapasitas_log (waktu, organik, anorganik, residu) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), organik, anorganik, residu),
    )
    conn.commit()
    conn.close()


def ambil_kapasitas_terbaru():
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM kapasitas_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def ambil_kapasitas_history(limit=24):
    """Ambil N data terakhir untuk grafik (urut waktu naik)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM kapasitas_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def simpan_klasifikasi(nama_objek, jenis, confidence, gambar_url=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO klasifikasi_log (waktu, nama_objek, jenis, confidence, gambar_url) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nama_objek, jenis, confidence, gambar_url),
    )
    conn.commit()
    conn.close()


def ambil_klasifikasi_terbaru(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM klasifikasi_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buat_notifikasi(tipe, judul, pesan):
    conn = get_conn()
    conn.execute(
        "INSERT INTO notifikasi (waktu, tipe, judul, pesan) VALUES (?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipe, judul, pesan),
    )
    conn.commit()
    conn.close()


def ambil_notifikasi_terbaru(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notifikasi ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
