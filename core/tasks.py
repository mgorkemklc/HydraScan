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

    # --- LOGLAMA FONKSİYONU ---
    # Bu fonksiyon modüllerden gelen mesajları Redis üzerinden arayüze taşır
    def log_callback(message):
        docker_helper.log_to_redis(scan_id, message)

    scan.celery_task_id = self.request.id
    scan.status = 'RUNNING'
    scan.save()
    
    local_output_dir = os.path.join(settings.MEDIA_ROOT, f"scan_outputs/scan_{scan.id}")
    os.makedirs(local_output_dir, exist_ok=True)
    scan.output_directory = local_output_dir
    scan.save()

    domain_input = scan.target_full_domain
    internal_ip_range = scan.internal_ip_range
    image_name = "pentest-araci-kali:v1.5"
    
    recon_tools = ["whois", "subfinder", "amass", "dig", "nmap"]
    web_tools = ["gobuster", "nikto", "nuclei", "sqlmap", "dalfox", "commix", "wapiti", "hydra"]

    try:
        log_callback(f"\n[+] Scan ID {scan.id} için tarama başlatılıyor...\n")
        
        # --- PARALEL İŞLEM ---
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            
            # Recon Modülü
            futures.append(executor.submit(
                recon_module.run_reconnaissance, 
                domain_input, 
                local_output_dir, 
                image_name, 
                recon_tools,
                log_callback # Loglama eklendi
            ))
            
            # Web Modülü
            futures.append(executor.submit(
                web_app_module.run_web_tests, 
                domain_input, 
                local_output_dir, 
                image_name, 
                web_tools,
                log_callback # Loglama eklendi
            ))
            
            # API Modülü
            futures.append(executor.submit(
                api_module.run_api_tests, 
                domain_input, 
                image_name, 
                local_output_dir,
                [], 
                log_callback # Loglama eklendi
            ))

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    logging.error(f"[-] Bir işlem hata verdi: {exc}")
                    log_callback(f"[-] Kritik Hata: {exc}\n")
        
        log_callback("\n[+] Paralel görevler tamamlandı.\n")
        
        if internal_ip_range:
            internal_network_module.run_internal_tests(internal_ip_range, local_output_dir, image_name)

    except Exception as e:
        logging.exception(f"[-] Scan ID {scan.id} çöktü: {e}")
        scan.status = 'FAILED'
        scan.save()
        return

    # --- RAPORLAMA (ARTIK LOGLU) ---
    try:
        log_callback(f"\n[*] AI Raporu hazırlanıyor...\n")
        scan.status = 'REPORTING'
        scan.save()
        
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        
        # BURADA stream_callback PARAMETRESİNİ GÖNDERİYORUZ
        report_json_path = report_module.generate_report(
            local_output_dir,
            domain_input,
            api_key,
            stream_callback=log_callback 
        )
        
        if report_json_path and os.path.exists(report_json_path):
            scan.report_file_path = report_json_path
            scan.status = 'COMPLETED'
            log_callback(f"[+] Rapor ve Analiz Tamamlandı. Dosya: {os.path.basename(report_json_path)}\n")
        else:
            log_callback(f"[-] Rapor oluşturulamadı (Dosya oluşmadı).\n")
            scan.status = 'COMPLETED' 
    
    except Exception as e:
        logging.exception(f"[-] Raporlama hatası: {e}")
        log_callback(f"[-] Raporlama sırasında hata oluştu: {e}\n")
        scan.status = 'FAILED'

    scan.completed_at = datetime.now()
    scan.save()
    log_callback(f"[+] İşlem Bitti. Durum: {scan.status}\n")