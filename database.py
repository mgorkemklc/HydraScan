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
    
    # 1. ŞİRKETLER (TENANTS) TABLOSU
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at DATETIME
    );
    """)

    # 2. KULLANICILAR TABLOSU (Rol ve Şirket ID Eklendi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Musteri', -- Rol: Superadmin, Admin, Pentester, Musteri
        company_id INTEGER,                   -- Hangi şirkete/tenant'a bağlı olduğu
        created_at DATETIME,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    );
    """)

    # 3. TARAMALAR TABLOSU (Şirket ve Müşteri İlişkisi Eklendi)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,             -- Taramayı başlatan personel (Pentester/Admin)
        company_id INTEGER,          -- Taramayı yapan şirket
        customer_id INTEGER,         -- Taramanın yapıldığı müşteri (Musteri rolündeki user_id)
        target_full_domain TEXT NOT NULL,
        internal_ip_range TEXT,
        apk_file_s3_path TEXT, 
        status TEXT NOT NULL DEFAULT 'PENDING',
        output_directory TEXT,
        report_file_path TEXT,
        created_at DATETIME NOT NULL,
        completed_at DATETIME,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (company_id) REFERENCES companies(id),
        FOREIGN KEY (customer_id) REFERENCES users(id)
    );
    """)
    
    # --- VARSAYILAN (TEST) VERİLERİNİN OLUŞTURULMASI ---
    try:
        now = datetime.datetime.now()
        default_pass = hashlib.sha256("admin123".encode()).hexdigest()
        
        # Superadmin (Şirket bağımsız, en yetkili)
        cursor.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)", 
                       ("superadmin", default_pass, "Superadmin", now))
        
        # Varsayılan bir Pentest Şirketi (Tenant)
        cursor.execute("INSERT INTO companies (name, created_at) VALUES (?, ?)", ("Hydra Security Ltd.", now))
        company_id = cursor.lastrowid
        
        # Şirket Yöneticisi (Admin)
        cursor.execute("INSERT INTO users (username, password_hash, role, company_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                       ("admin", default_pass, "Admin", company_id, now))
        
        # Şirket Çalışanı (Pentester)
        cursor.execute("INSERT INTO users (username, password_hash, role, company_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                       ("pentester", default_pass, "Pentester", company_id, now))
                       
        # Müşteri (Sadece kendi raporlarını görebilir)
        cursor.execute("INSERT INTO users (username, password_hash, role, company_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                       ("musteri", default_pass, "Musteri", company_id, now))

    except sqlite3.IntegrityError:
        pass # Veriler zaten varsa geç

    conn.commit()
    conn.close()

# --- KULLANICI İŞLEMLERİ ---
def login_check(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user:
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if input_hash == user['password_hash']:
            # Dictionary gibi davranması için dict'e çeviriyoruz
            return dict(user) 
    return None

def register_user(username, password, role="Musteri", company_id=None):
    conn = get_db_connection()
    pass_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        conn.execute("INSERT INTO users (username, password_hash, role, company_id, created_at) VALUES (?, ?, ?, ?, ?)", 
                     (username, pass_hash, role, company_id, datetime.datetime.now()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- TARAMA İŞLEMLERİ ---
def create_scan(scan_data, user_id, company_id=None, customer_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    
    cursor.execute("""
    INSERT INTO scans (
        user_id, company_id, customer_id, target_full_domain, internal_ip_range, apk_file_s3_path, 
        status, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        company_id,
        customer_id,
        scan_data.get('domain', ''),
        scan_data.get('internal_ip'),
        scan_data.get('apk_path'),
        'PENDING',
        now
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

def insert_imported_scan(user_id, domain, status, output_dir, report_path, created_at, company_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    check = cursor.execute("SELECT id, status FROM scans WHERE output_directory = ?", (output_dir,)).fetchone()
    
    if check:
        scan_id = check['id']
        current_status = check['status']
        if current_status != "COMPLETED" and report_path and os.path.exists(report_path):
            now = datetime.datetime.now()
            cursor.execute("""
                UPDATE scans 
                SET status = 'COMPLETED', report_file_path = ?, completed_at = ? 
                WHERE id = ?
            """, (report_path, now, scan_id))
            conn.commit()
        conn.close()
        return scan_id

    cursor.execute("""
    INSERT INTO scans (
        user_id, company_id, target_full_domain, status, output_directory, report_file_path, created_at, completed_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, company_id, domain, status, output_dir, report_path, created_at, created_at))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id

# YETKİ KONTROLLÜ TARAMA GETİRME (RBAC)
def get_all_scans(user):
    conn = get_db_connection()
    role = user['role']
    user_id = user['id']
    company_id = user['company_id']
    
    if role == "Superadmin":
        # Superadmin tüm sistemdeki taramaları görür
        rows = conn.execute("SELECT * FROM scans ORDER BY created_at DESC").fetchall()
    elif role in ["Admin", "Pentester"]:
        # Admin ve Pentester sadece kendi şirketinin taramalarını görür
        rows = conn.execute("SELECT * FROM scans WHERE company_id = ? ORDER BY created_at DESC", (company_id,)).fetchall()
    elif role == "Musteri":
        # Müşteri sadece kendisine atanmış taramaları görür
        rows = conn.execute("SELECT * FROM scans WHERE customer_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    else:
        rows = []
        
    conn.close()
    return rows

def get_scan_by_id(scan_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

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

# --- KULLANICI YÖNETİMİ (SUPERADMIN İÇİN) ---
def get_all_users():
    conn = get_db_connection()
    # Kullanıcıları ve bağlı oldukları şirket isimlerini getir
    rows = conn.execute("""
        SELECT u.id, u.username, u.role, c.name as company_name 
        FROM users u 
        LEFT JOIN companies c ON u.company_id = c.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_user(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()