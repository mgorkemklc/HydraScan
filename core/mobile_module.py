import os
import time
import requests
import logging

# MobSF API Yapılandırması
MOBSF_URL = "http://127.0.0.1:8000"
API_KEY = "hydrascan_secret_key"
HEADERS = {'Authorization': API_KEY}

def run_mobile_tests(file_path, output_dir, selected_tools=[], stream_callback=None):
    if stream_callback: stream_callback(f"\n[+] Mobil Analiz Motoru Başlatıldı.")
    if stream_callback: stream_callback(f"[*] İşlenen Dosya: {os.path.basename(file_path)}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        if "mobsf_sast" in selected_tools:
            # 1. Dosyayı MobSF'e Yükleme (Upload)
            if stream_callback: stream_callback("[*] Dosya MobSF sunucusuna yükleniyor...")
            
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                upload_res = requests.post(f"{MOBSF_URL}/api/v1/upload", headers=HEADERS, files=files, timeout=60)
            
            if upload_res.status_code != 200:
                raise Exception(f"MobSF Yükleme Hatası: {upload_res.text}")
                
            upload_data = upload_res.json()
            scan_hash = upload_data.get('hash')
            file_type = upload_data.get('scan_type')
            file_name = upload_data.get('file_name')
            
            if stream_callback: stream_callback(f"[+] Yükleme Başarılı. (Hash: {scan_hash[:8]}... Type: {file_type})")
            
            # 2. Statik Analizi Başlatma (Scan)
            if stream_callback: stream_callback("[*] Derin Statik Analiz (SAST) başlatıldı. Bu işlem dosya boyutuna göre birkaç dakika sürebilir...")
            
            scan_payload = {'hash': scan_hash, 'scan_type': file_type, 'file_name': file_name}
            scan_res = requests.post(f"{MOBSF_URL}/api/v1/scan", headers=HEADERS, data=scan_payload, timeout=600) # 10 dk timeout
            
            if scan_res.status_code != 200:
                raise Exception(f"MobSF Analiz Hatası: {scan_res.text}")
                
            if stream_callback: stream_callback("[+] Statik Analiz tamamlandı. Raporlar çekiliyor...")
            
            # 3. PDF Raporunu İndirme
            pdf_payload = {'hash': scan_hash}
            pdf_res = requests.post(f"{MOBSF_URL}/api/v1/download_pdf", headers=HEADERS, data=pdf_payload, stream=True)
            
            if pdf_res.status_code == 200:
                pdf_path = os.path.join(output_dir, "MobSF_SAST_Report.pdf")
                with open(pdf_path, 'wb') as f:
                    for chunk in pdf_res.iter_content(chunk_size=8192):
                        f.write(chunk)
                if stream_callback: stream_callback(f"[+] PDF Raporu oluşturuldu: {pdf_path}")
            
            # 4. JSON Verisini Çekme (Veritabanı işlemleri için)
            json_payload = {'hash': scan_hash}
            json_res = requests.post(f"{MOBSF_URL}/api/v1/report_json", headers=HEADERS, data=json_payload)
            if json_res.status_code == 200:
                json_path = os.path.join(output_dir, "MobSF_Report.json")
                with open(json_path, 'w', encoding='utf-8') as f:
                    f.write(json_res.text)

        if "frida_dast" in selected_tools:
            if stream_callback: stream_callback("\n[!] Dinamik Analiz (Frida) altyapısı Android Emülatörü gerektirir.")
            if stream_callback: stream_callback("[*] Frida DAST modülü yapılandırma aşamasındadır (Phase 2).")

        if stream_callback: stream_callback("\n[√] Mobil Modül işlemleri başarıyla tamamlandı.")
        return True

    except requests.exceptions.ConnectionError:
        if stream_callback: stream_callback("\n[!] HATA: MobSF sunucusuna bağlanılamadı. Docker konteynerinin çalıştığından emin olun.")
        return False
    except Exception as e:
        if stream_callback: stream_callback(f"\n[!] BEKLENMEYEN HATA: {str(e)}")
        logging.error(f"Mobile Module Error: {str(e)}")
        return False