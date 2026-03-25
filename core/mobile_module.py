import os
import requests
import json
from .docker_helper import run_command_in_docker

# MobSF Ayarları (Bunu daha sonra app.py -> Ayarlar sekmesinden çekeceğiz)
MOBSF_URL = "http://127.0.0.1:8000"
MOBSF_API_KEY = "d1b3111b6f8157a4bf9462ac52114f84c4d7e28ca527c51b588e4febe7c70df7" # DİKKAT: Kendi MobSF API Key'ini buraya yapıştıracaksın

def run_mobile_tests(file_path, output_dir, image_name, stream_callback=None):
    """
    Belirtilen mobil uygulama (.apk, .aab, .ipa) üzerinde SAST/DAST analizleri yapar.
    Bulduğu backend API URL'lerini liste olarak geri döndürür.
    """
    def log(msg):
        if stream_callback: stream_callback(msg + "\n")
        else: print(msg)

    log("\n[+] Mobil Uygulama (Gelişmiş SAST & API Routing) modülü başlatılıyor...")

    if not os.path.exists(file_path):
        log(f"[-] Hata: Belirtilen mobil uygulama dosyası bulunamadı: {file_path}")
        return []

    file_dir = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    ext = filename.split('.')[-1].lower()

    if ext not in ['apk', 'aab', 'xapk', 'ipa']:
        log(f"[-] Hata: Desteklenmeyen dosya formatı ({ext}). Lütfen .apk, .aab veya .ipa yükleyin.")
        return []

    # Zincirleme saldırı için API/Backend linklerini tutacağımız küme
    extracted_urls = set()

    # ==========================================================
    # 1. TEMEL ARAÇLAR (Sadece Android için apktool & apkleaks)
    # ==========================================================
    if ext in ['apk', 'aab', 'xapk']:
        docker_mount_args = ['-v', f'{os.path.abspath(file_dir)}:/app']
        
        log("[*] APKLeaks ile hardcoded sırlar ve Backend URL'leri çıkarılıyor...")
        apkleaks_out = os.path.join(output_dir, "apkleaks_ciktisi.txt")
        run_command_in_docker(f"apkleaks -f /app/{filename}", apkleaks_out, image_name, extra_docker_args=docker_mount_args)

        # Çıktıdan URL'leri ayıkla (API Routing için)
        if os.path.exists(apkleaks_out):
            with open(apkleaks_out, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "http://" in line or "https://" in line:
                        parts = line.strip().split()
                        for p in parts:
                            if p.startswith("http"): extracted_urls.add(p)

        log("[*] Apktool ile kaynak kod çıkarılıyor (Manuel analiz için klasöre atılacak)...")
        apktool_out = os.path.join(output_dir, "apktool_ciktisi.txt")
        run_command_in_docker(f"apktool d /app/{filename} -o /output/apktool_decompiled -f", apktool_out, image_name, extra_docker_args=docker_mount_args)
    
    elif ext == 'ipa':
        log("[*] iOS Uygulaması (.ipa) algılandı. Temel araçlar atlanıyor, doğrudan MobSF'e gönderilecek.")

    # ==========================================================
    # 2. MOBSF ENTEGRASYONU (Derin Statik Analiz)
    # ==========================================================
    if MOBSF_API_KEY:
        log(f"[*] MobSF API'sine bağlanılıyor ({MOBSF_URL})...")
        mobsf_results = run_mobsf_analysis(file_path, output_dir, log)
        
        # MobSF'in bulduğu URL'leri de API Routing listesine ekle
        if mobsf_results and "urls" in mobsf_results:
            for item in mobsf_results["urls"]:
                if isinstance(item, dict) and "url" in item:
                    extracted_urls.add(item["url"])
                elif isinstance(item, str):
                    extracted_urls.add(item)
    else:
        log("[-] MobSF API Key boş! Derin SAST analizi ve Kurumsal Mobil PDF Raporu atlanıyor.")
        log("    (Lütfen MobSF'i ayağa kaldırıp API key'i koda ekleyin)")

    # ==========================================================
    # 3. DAST (DİNAMİK ANALİZ) ALTYAPISI - (Sonraki Aşama)
    # ==========================================================
    log("[*] DAST (Dinamik Analiz) ve Frida Hooking mimarisi hazır. (Gelecek güncellemede aktif edilecek)")

    log(f"\n[+] Mobil Testler Bitti. Toplam {len(extracted_urls)} potansiyel Backend URL'si bulundu.")
    
    # URL'leri liste olarak app.py'ye geri gönder
    return list(extracted_urls)


def run_mobsf_analysis(file_path, output_dir, log):
    """MobSF REST API'sini kullanarak dosyayı yükler, tarar ve raporu (JSON+PDF) çeker."""
    headers = {'Authorization': MOBSF_API_KEY}
    
    try:
        # 1. DOSYAYI YÜKLE (UPLOAD)
        log("   -> Uygulama MobSF sunucusuna yükleniyor...")
        upload_url = f"{MOBSF_URL}/api/v1/upload"
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
            res = requests.post(upload_url, headers=headers, files=files, timeout=60)
        
        if res.status_code != 200:
            log(f"   [-] MobSF Yükleme Hatası: {res.text}")
            return None
        
        data = res.json()
        scan_type = data.get('scan_type')
        file_name = data.get('file_name')
        file_hash = data.get('hash')
        log(f"   [+] Yükleme Başarılı. Dosya Hash: {file_hash}")

        # 2. TARAMAYI BAŞLAT (SCAN)
        log("   -> MobSF Derin Analizi başlatıldı (Bu işlem uygulamanın boyutuna göre birkaç dakika sürebilir)...")
        scan_url = f"{MOBSF_URL}/api/v1/scan"
        scan_res = requests.post(scan_url, headers=headers, data={'scan_type': scan_type, 'file_name': file_name, 'hash': file_hash}, timeout=600)
        
        if scan_res.status_code == 200:
            log("   [+] Tarama bitti. Raporlar indiriliyor...")
            scan_data = scan_res.json()
            
            # JSON Raporunu Kaydet
            with open(os.path.join(output_dir, "mobsf_raporu.json"), "w", encoding="utf-8") as rf:
                json.dump(scan_data, rf, indent=4)
            
            # 3. PDF RAPORUNU İNDİR (DOWNLOAD PDF)
            pdf_url = f"{MOBSF_URL}/api/v1/download_pdf"
            pdf_res = requests.post(pdf_url, headers=headers, data={'hash': file_hash, 'scan_type': scan_type}, stream=True)
            if pdf_res.status_code == 200:
                pdf_path = os.path.join(output_dir, "MobSF_Mobil_Rapor.pdf")
                with open(pdf_path, 'wb') as pf:
                    for chunk in pdf_res.iter_content(chunk_size=8192):
                        pf.write(chunk)
                log(f"   [+] MobSF Kurumsal PDF Raporu oluşturuldu: {pdf_path}")
            
            return scan_data
        else:
            log(f"   [-] MobSF Tarama Hatası: {scan_res.text}")
            
    except Exception as e:
        log(f"   [-] MobSF Bağlantı/Zaman Aşımı Hatası: {str(e)}")
        log("       (MobSF Docker konteynerinin çalıştığından emin olun)")
        
    return None