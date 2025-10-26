# database.py

import sqlite3
import os
import datetime

# Veritabanı dosyamızın adı (app.py ile aynı klasörde oluşacak)
DB_FILE = "hydrascan_local.db"

def get_db_connection():
    """Veritabanı bağlantısı oluşturur."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Sonuçlara sütun adlarıyla erişmemizi sağlar
    return conn

def init_db():
    """
    Veritabanını ve 'scans' tablosunu (eğer yoksa) oluşturur.
    Bu, Django'nun 'migrate' komutunun yerini alır.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Django modeline (core/models.py) benzer bir tablo oluşturuyoruz
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_full_domain TEXT NOT NULL,
        internal_ip_range TEXT,
        apk_file_s3_path TEXT, 
        
        -- Kablosuz modül için yeni alanlar
        wifi_iface TEXT,
        wifi_bssid TEXT,
        wifi_channel TEXT,

        status TEXT NOT NULL DEFAULT 'PENDING',
        output_directory TEXT,
        report_file_path TEXT,
        
        created_at DATETIME NOT NULL,
        completed_at DATETIME
    );
    """)
    
    conn.commit()
    conn.close()
    print("[Veritabanı] Veritabanı başarıyla başlatıldı.")

def create_scan(scan_data):
    """
    Veritabanına yeni bir tarama kaydı ekler.
    'scan_data' arayüzden gelen dict verisidir.
    Yeni oluşturulan taramanın ID'sini döndürür.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    
    cursor.execute("""
    INSERT INTO scans (
        target_full_domain, internal_ip_range, apk_file_s3_path, 
        wifi_iface, wifi_bssid, wifi_channel, 
        status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scan_data['domain'],
        scan_data.get('internal_ip'),
        scan_data.get('apk_path'),
        scan_data.get('wifi_iface'),
        scan_data.get('wifi_bssid'),
        scan_data.get('wifi_channel'),
        'PENDING',
        now
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return new_id

def get_all_scans():
    """
    Gösterge Paneli (Dashboard) için tüm taramaları en yeniden eskiye doğru çeker.
    """
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM scans ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows

def get_scan_by_id(scan_id):
    """Tek bir taramanın detaylarını çeker."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return row

def update_scan_status(scan_id, status):
    """Bir taramanın durumunu günceller (örn: PENDING -> RUNNING)."""
    conn = get_db_connection()
    conn.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
    conn.commit()
    conn.close()

def set_scan_output_directory(scan_id, directory_path):
    """Taramanın çıktı klasörünün yolunu kaydeder."""
    conn = get_db_connection()
    conn.execute("UPDATE scans SET output_directory = ? WHERE id = ?", (directory_path, scan_id))
    conn.commit()
    conn.close()

def complete_scan(scan_id, report_path, status="COMPLETED"):
    """
    Taramayı 'Tamamlandı' (veya Hata) olarak işaretler, 
    rapor yolunu ve bitiş zamanını kaydeder.
    """
    conn = get_db_connection()
    now = datetime.datetime.now()
    conn.execute(
        "UPDATE scans SET status = ?, report_file_path = ?, completed_at = ? WHERE id = ?",
        (status, report_path, now, scan_id)
    )
    conn.commit()
    conn.close()

def delete_scan_from_db(scan_id):
    """Bir tarama kaydını veritabanından siler."""
    conn = get_db_connection()
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()