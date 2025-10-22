import os
import time
import logging
from celery import shared_task
from .models import Scan
from datetime import datetime

# Kendi modüllerini import et
# Proje yapına göre (örn: hydrascan_project.hydrascan_app.docker_helper)
# import docker_helper
# import recon_module
# import web_app_module
# ... ve diğerleri ...
# Şimdilik aynı dizindeymiş gibi varsayıyorum:
import docker_helper
import recon_module
import web_app_module
import api_module
import internal_network_module
import cloud_module
import mobile_module
import report_module
import concurrent.futures

# main.py'deki fonksiyonları buraya taşıyabiliriz
def create_output_directory(scan_id):
    """
    Çıktıların saklanacağı, Scan ID'sine özel benzersiz bir dizin oluşturur.
    """
    # Django'nun media dizinini kullanmak en iyisidir
    output_dir = f"media/scan_outputs/{scan_id}" 
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_dir, os.path.abspath(output_dir)

def get_clean_domain(domain_with_port):
    if ':' in domain_with_port:
        return domain_with_port.split(':')[0]
    return domain_with_port


# BU, SENİN main() FONKSİYONUNUN YENİ HALİ
@shared_task
def run_hydrascan_task(scan_id):
    
    # 1. Verileri input() yerine Veritabanından Çek
    try:
        scan = Scan.objects.get(id=scan_id)
    except Scan.DoesNotExist:
        print(f"[-] Hata: Scan ID {scan_id} bulunamadı.")
        return

    # 2. Durumu Güncelle ve Çıktı Dizini Oluştur
    scan.status = 'RUNNING'
    scan.save()
    
    # main.py'deki create_output_directory'nin yeni hali
    relative_output_dir, absolute_output_dir = create_output_directory(scan.id)
    scan.output_directory = relative_output_dir # Yolu veritabanına kaydet
    scan.save()

    # main.py'deki değişkenleri veritabanından al
    domain_input = scan.target_full_domain
    clean_domain = get_clean_domain(domain_input)
    internal_ip_range = scan.internal_ip_range
    apk_file_path = scan.apk_file_s3_path # Bu yolu S3'ten alacak şekilde güncellemeliyiz
    api_key = scan.gemini_api_key
    
    aws_keys = {}
    if scan.aws_access_key:
        aws_keys['access_key'] = scan.aws_access_key
        aws_keys['secret_key'] = scan.aws_secret_key
        aws_keys['region'] = scan.aws_region

    # --- ÖNEMLİ DEĞİŞİKLİK ---
    # Docker imajı oluşturma (build) işlemi, her taramada ÇALIŞTIRILMAMALI.
    # Bu, sunucu kurulurken (deploy) bir kez yapılır.
    # image_name = docker_helper.build_custom_image() # <-- BU SATIRI KALDIR
    image_name = "pentest-araci-kali:v1.5" # İmajın adını sabit olarak al
    
    # --- main.py'deki Test Akışının AYNISI ---
    try:
        print(f"\n[+] Scan ID {scan.id} için paralel görevler başlatılıyor...")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                # Senin fonksiyonların, ama 'output_dir' olarak yeni yolu veriyoruz
                executor.submit(recon_module.run_reconnaissance, clean_domain, domain_input, absolute_output_dir, image_name),
                executor.submit(web_app_module.run_web_tests, domain_input, absolute_output_dir, image_name),
                executor.submit(api_module.run_api_tests, domain_input, absolute_output_dir, image_name)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        if internal_ip_range:
            internal_network_module.run_internal_tests(internal_ip_range, absolute_output_dir, image_name)
        if aws_keys:
            cloud_module.run_cloud_tests(
                aws_keys['access_key'], aws_keys['secret_key'], aws_keys['region'],
                absolute_output_dir, image_name
            )
        if apk_file_path:
            # Burayı S3'ten dosyayı indirmek için güncellemen gerekecek
            mobile_module.run_mobile_tests(apk_file_path, absolute_output_dir, image_name)

    except Exception as e:
        print(f"[-] Testler sırasında hata: {e}")
        scan.status = 'FAILED'
        scan.save()
        return

    # --- Raporlama ---
    print(f"\n[+] Scan ID {scan.id} için rapor oluşturuluyor...")
    scan.status = 'REPORTING'
    scan.save()
    
    # report_module.py'yi de 'report_file_path' döndürecek şekilde düzenlemeliyiz
    report_file_abs_path = report_module.generate_report(absolute_output_dir, domain_input, api_key)
    
    # Raporun göreceli yolunu DB'ye kaydet
    scan.report_file_path = report_file_abs_path.replace(os.path.abspath('media/'), 'media/')
    scan.status = 'COMPLETED'
    scan.completed_at = datetime.now()
    scan.save()
    
    print(f"\n[+] Scan ID {scan.id} tamamlandı. Rapor şurada: {scan.report_file_path}")