from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import threading
import os
import concurrent.futures
import json

# --- HYDRASCAN ÇEKİRDEK MODÜLLERİ ---
# Eski app_eski.py dosyanızda kullandığınız modülleri içeri aktarıyoruz.
import database
from core import recon_module, web_app_module, mobile_module, report_module, internal_network_module

app = FastAPI(title="HydraScan Local API")

# C# Arayüzüne gönderilecek canlı terminal logları havuzu
terminal_logs = [
    "[*] HydraScan Enterprise API Motoru Başlatıldı.",
    "[*] C# WPF Arayüzü ile bağlantı dinleniyor...",
    "[+] Sistem hazır. Hedef girin ve taramayı başlatın."
]

class ScanRequest(BaseModel):
    target: str
    scan_type: str

def log_msg(msg):
    """Gelen logları C#'ın çekebilmesi için listeye ekler"""
    terminal_logs.append(msg)
    print(msg) # Python kendi siyah konsoluna da bassın

@app.get("/api/logs")
def get_logs():
    """C# arayüzü saniyede bir bu adrese gelip biriken logları çekecek"""
    global terminal_logs
    current_logs = terminal_logs.copy()
    terminal_logs.clear() # C# logları okuduktan sonra havuzu temizle ki aynı loglar tekrar gitmesin
    return {"logs": current_logs}

@app.get("/api/stats")
def get_stats():
    """C# arayüzü saniyede bir veritabanı istatistiklerini buradan çekecek"""
    try:
        user = database.login_check("superadmin", "admin123")
        scans = database.get_all_scans(user)
        total = len(scans)
        active = sum(1 for s in scans if s['status'] in ["RUNNING", "PENDING", "REPORTING"])
        failed = sum(1 for s in scans if s['status'] == "FAILED")
        return {"total": total, "active": active, "failed": failed}
    except:
        return {"total": 0, "active": 0, "failed": 0}

@app.get("/api/reports")
def get_reports():
    """Tüm tarama geçmişini listeler"""
    try:
        user = database.login_check("superadmin", "admin123")
        scans = database.get_all_scans(user)
        # Sadece Frontend'in ihtiyacı olan alanları dönüyoruz, ayrıca sqlite3.Row parse hatası olmasın diye dictionary'e çeviriyoruz
        reports = []
        for s in scans:
            reports.append({
                "id": s["id"],
                "target_full_domain": s["target_full_domain"],
                "status": s["status"],
                "created_at": str(s["created_at"])
            })
        return {"reports": reports}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/reports/{scan_id}")
def get_report_detail(scan_id: int):
    """Belirli bir taramanın detaylı JSON raporunu döndürür"""
    try:
        scan = database.get_scan_by_id(scan_id)
        if not scan:
            return {"error": "Tarama bulunamadı"}
            
        path = None
        try:
            path = scan['report_file_path']
        except:
            pass
            
        if path and path.endswith(".html"): 
            path = path.replace(".html", ".json")
            
        report_data = {}
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
                
        return {"report_data": report_data, "scan_info": {
             "id": scan["id"], 
             "target": scan["target_full_domain"], 
             "status": scan["status"]
        }}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scan")
def start_scan(req: ScanRequest):
    """C# arayüzünden Başlat butonuna basıldığında bu fonksiyon tetiklenir"""
    # Arayüzün donmaması ve API'nin kilitlenmemesi için asıl taramayı ayrı bir Thread'e gönderiyoruz
    threading.Thread(target=run_scan_logic, args=(req.target, req.scan_type), daemon=True).start()
    return {"status": "success"}

def run_scan_logic(target, scan_type):
    """HydraScan'in Asıl Sızma Testi İşlemleri (Eski app_eski.py'den taşındı)"""
    log_msg(f"\n[*] {scan_type.upper()} taraması başlatılıyor: {target}")
    
    try:
        # 1. Veritabanı Kaydı
        user = database.login_check("superadmin", "admin123")
        scan_data = {
            "domain": target, 
            "scan_type": scan_type, 
            "apk_path": target if scan_type=="mobile" else None, 
            "gemini_key": ""
        }
        scan_id = database.create_scan(scan_data, user['id'], user['company_id'], user['id'])
        
        database.update_scan_status(scan_id, 'RUNNING')
        out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
        if not os.path.exists(out): os.makedirs(out)
        database.set_scan_output_directory(scan_id, out)
        
        img = "pentest-araci-kali:v1.5"
        selected_tools = ["nmap", "nuclei", "gobuster"] # Varsayılan çalışacak araçlar

        log_msg(f"[*] Veritabanı görev kaydı oluşturuldu (Görev ID: {scan_id})")
        log_msg("[*] Alt modüller ve Docker araçları tetiklendi...")

        # 2. Çoklu İş Parçacığı ile Modülleri Çalıştırma
        with concurrent.futures.ThreadPoolExecutor() as ex:
            futures = []
            if scan_type == "web":
                futures.append(ex.submit(recon_module.run_reconnaissance, target, out, img, selected_tools))
                # stream_callback sayesinde Nmap logları saniye saniye C# ekranına akacak!
                futures.append(ex.submit(web_app_module.run_web_tests, target, out, img, selected_tools, stream_callback=log_msg, custom_wordlist=None))
            elif scan_type == "network":
                futures.append(ex.submit(internal_network_module.run_network_tests, target, out, img, selected_tools))
            elif scan_type == "mobile":
                futures.append(ex.submit(mobile_module.run_mobile_tests, target, out, img, stream_callback=log_msg))

            # Hataları Yakala
            for f in concurrent.futures.as_completed(futures):
                try: 
                    f.result()
                except Exception as e: 
                    log_msg(f"[-] Modül Hatası: {str(e)}")

        # 3. Raporlama Aşaması
        log_msg("\n[*] Araçlar tamamlandı. AI Raporu hazırlanıyor...")
        database.update_scan_status(scan_id, 'REPORTING')
        path = report_module.generate_report(out, target, "")
        
        status = "COMPLETED" if path else "FAILED"
        database.complete_scan(scan_id, path, status)
        log_msg(f"[+] Tarama Başarıyla Bitti. Son Durum: {status}")

    except Exception as e:
        log_msg(f"[-] Sistem Kritik Hatası: {str(e)}")
        database.complete_scan(scan_id, None, "FAILED")

if __name__ == "__main__":
    print("==================================================")
    print(" 🐉 HydraScan API Motoru Başlatılıyor...")
    print("==================================================")
    # FastAPI sunucusunu ayağa kaldırıyoruz (127.0.0.1:8000)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")