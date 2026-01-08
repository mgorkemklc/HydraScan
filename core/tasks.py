# core/tasks.py

import os
import logging
from celery import shared_task
from .models import Scan
from datetime import datetime
from django.conf import settings
import concurrent.futures

# Modül importları
from . import docker_helper
from . import recon_module
from . import web_app_module
from . import api_module
from . import internal_network_module
# cloud_module AWS olduğu için kaldırdık veya pas geçtik
from . import report_module

def get_clean_domain(domain_with_port):
    if ':' in domain_with_port:
        return domain_with_port.split(':')[0]
    return domain_with_port

@shared_task(bind=True)
def run_hydrascan_task(self, scan_id):
    try:
        scan = Scan.objects.get(id=scan_id)
    except Scan.DoesNotExist:
        logging.error(f"[-] Hata: Scan ID {scan_id} bulunamadı.")
        return

    scan.celery_task_id = self.request.id
    scan.status = 'RUNNING'
    scan.save()
    
    # --- YEREL KLASÖR AYARLAMASI ---
    # S3 yerine projenin media klasörüne yazacağız.
    local_output_dir = os.path.join(settings.MEDIA_ROOT, f"scan_outputs/scan_{scan.id}")
    os.makedirs(local_output_dir, exist_ok=True)
    
    scan.output_directory = local_output_dir
    scan.save()
    # -------------------------------

    domain_input = scan.target_full_domain
    clean_domain = get_clean_domain(domain_input)
    internal_ip_range = scan.internal_ip_range
    
    # API key settings'den alınır
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    image_name = "pentest-araci-kali:v1.5"
    
    # Araç Listeleri (Burayı veritabanından veya dinamik alabilirsin, şimdilik sabit)
    recon_tools = ["whois", "subfinder", "amass", "dig", "nmap"]
    web_tools = ["gobuster", "nikto", "nuclei", "sqlmap", "dalfox", "commix", "wapiti"]
    # api_tools listesi şu an api_module içinde sabit, parametre gerekmiyor

    try:
        logging.info(f"\n[+] Scan ID {scan.id} için PARALEL görevler başlatılıyor...")
        
        # --- PARALEL İŞLEM (DEADLOCK OLMADAN) ---
        # S3 client göndermediğimiz için takılma yapmayacak.
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            
            # 1. Recon Modülü
            futures.append(executor.submit(
                recon_module.run_reconnaissance, 
                domain_input, 
                local_output_dir, # output_dir
                image_name, 
                recon_tools       # selected_tools
            ))
            
            # 2. Web Modülü
            futures.append(executor.submit(
                web_app_module.run_web_tests, 
                domain_input, 
                local_output_dir, # output_dir
                image_name, 
                web_tools         # selected_tools
            ))
            
            # 3. API Modülü (Not: api_module parametre sırası farklı olabilir, kontrol ettim: domain, image, output)
            futures.append(executor.submit(
                api_module.run_api_tests, 
                domain_input, 
                image_name, 
                local_output_dir # output_dir sonda
            ))

            # Sonuçları bekle
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    logging.error(f"[-] Bir paralel işlem hata verdi: {exc}")
        
        logging.info("\n[+] Paralel görevler tamamlandı.")
        
        # Sıralı Modüller (İç Ağ vb.)
        if internal_ip_range:
            logging.info("--> İç Ağ Modülü çalıştırılıyor...")
            internal_network_module.run_internal_tests(internal_ip_range, local_output_dir, image_name)

        # Cloud modülü AWS gerektirdiği için tamamen çıkartıldı.

    except Exception as e:
        logging.exception(f"[-] Scan ID {scan.id} testler sırasında çöktü: {e}")
        scan.status = 'FAILED'
        scan.save()
        return

    # --- RAPORLAMA (YEREL) ---
    try:
        logging.info(f"\n[+] Scan ID {scan.id} için rapor oluşturuluyor...")
        scan.status = 'REPORTING'
        scan.save()
        
        # Report modülü artık S3 client istemiyor, sadece ID ve Domain alıyor
        # json rapor yolunu döndürecek
        report_json_path = report_module.generate_pentest_report(
            scan.id,
            domain_input,
            scan.user.id
        )
        
        if report_json_path and os.path.exists(report_json_path):
            # İsteğe bağlı PDF çevirme
            pdf_path = report_module.export_to_pdf(report_json_path)
            
            scan.report_file_path = pdf_path if pdf_path else report_json_path
            scan.status = 'COMPLETED'
            logging.info(f"\n[+] Rapor başarıyla oluşturuldu: {scan.report_file_path}")
        else:
            logging.error(f"[-] Rapor JSON dosyası oluşturulamadı.")
            # Yine de COMPLETED diyebiliriz, tarama bitti çünkü
            scan.status = 'COMPLETED' 
    
    except Exception as e:
        logging.exception(f"[-] Raporlama sırasında hata: {e}")
        scan.status = 'FAILED'

    scan.completed_at = datetime.now()
    scan.save()