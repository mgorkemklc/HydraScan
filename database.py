# database.py

import sqlite3
import os
import datetime
import hashlib

DB_FILE = "hydrascan_local.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Taramalar Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, -- Hangi kullanıcının taraması
        target_full_domain TEXT NOT NULL,
        internal_ip_range TEXT,
        apk_file_s3_path TEXT, 
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

    # Kullanıcılar Tablosu (YENİ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at DATETIME
    );
    """)
    
    # Varsayılan Admin Kullanıcısı (admin / admin123)
    try:
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)", 
                       ("admin", admin_pass, "admin", datetime.datetime.now()))
    except sqlite3.IntegrityError:
        pass # Zaten var

    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ ---
def login_check(username, password):
    """Kullanıcı adı ve şifreyi doğrular."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if user:
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash == user['password_hash']:
            return user # Başarılı
    return None

def register_user(username, password):
    """Yeni kullanıcı oluşturur (SaaS mantığı için)."""
    conn = get_db_connection()
    pass_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        conn.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)", 
                     (username, pass_hash, datetime.datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Kullanıcı adı dolu
    finally:
        conn.close()

# --- TARAMA İŞLEMLERİ ---
def create_scan(scan_data, user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    cursor.execute("""
    INSERT INTO scans (
        user_id, target_full_domain, internal_ip_range, apk_file_s3_path, 
        status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        scan_data['domain'],
        scan_data.get('internal_ip'),
        scan_data.get('apk_path'),
        'PENDING',
        now
    ))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def get_all_scans(user_id=None):
    """Eğer user_id verilirse sadece o kullanıcının taramalarını getirir."""
    conn = get_db_connection()
    if user_id:
        rows = conn.execute("SELECT * FROM scans WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM scans ORDER BY created_at DESC").fetchall() # Admin hepsi
    conn.close()
    return rows

def get_scan_by_id(scan_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return row

def update_scan_status(scan_id, status):
    conn = get_db_connection()
    conn.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
    conn.commit()
    conn.close()

def set_scan_output_directory(scan_id, directory_path):
    conn = get_db_connection()
    conn.execute("UPDATE scans SET output_directory = ? WHERE id = ?", (directory_path, scan_id))
    conn.commit()
    conn.close()

def complete_scan(scan_id, report_path, status="COMPLETED"):
    conn = get_db_connection()
    now = datetime.datetime.now()
    conn.execute(
        "UPDATE scans SET status = ?, report_file_path = ?, completed_at = ? WHERE id = ?",
        (status, report_path, now, scan_id)
    )
    conn.commit()
    conn.close()

def delete_scan_from_db(scan_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    conn.commit()
    conn.close()