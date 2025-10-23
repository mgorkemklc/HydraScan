# core/tasks.py (GÜNCELLENMİŞ İÇERİK)

import os
import time
import logging
from celery import shared_task
from .models import Scan
from datetime import datetime

# --- YENİ IMPORTLAR (S3 VE AYARLAR İÇİN) ---
import boto3
from django.conf import settings
# --- IMPORTLAR SONU ---

from . import docker_helper
from . import recon_module
from . import web_app_module
from . import api_module
from . import internal_network_module
from . import cloud_module
from . import mobile_module
from . import report_module
import concurrent.futures

# --- YENİ FONKSİYON ---
def get_s3_prefix_and_client(scan_id):
    # DİKKAT: settings.py'de S3 anahtarları olmadığı için,
    # bu fonksiyon ECS Görev Rolü'nü (IAM Role) kullanacaktır.
    # Yerelde test ederken hata alırsanız, boto3'e anahtarları
    # environment variable olarak (AWS_ACCESS_KEY_ID vb.) vermeniz gerekir.
    s3_client = boto3.client(
        's3',
        # Anahtarlar ECS Rolünden otomatik alınacak
        region_name=settings.AWS_S3_REGION_NAME
    )
    s3_prefix = f"media/scan_outputs/{scan_id}/"
    return s3_client, s3_prefix

def get_clean_domain(domain_with_port):
    if ':' in domain_with_port:
        return domain_with_port.split(':')[0]
    return domain_with_port

@shared_task
def run_hydrascan_task(scan_id):
    
    try:
        scan = Scan.objects.get(id=scan_id)
    except Scan.DoesNotExist:
        logging.error(f"[-] Hata: Scan ID {scan_id} bulunamadı.")
        return

    scan.status = 'RUNNING'
    scan.save()
    
    # --- DEĞİŞİKLİK: YEREL KLASÖR YERİNE S3 BAĞLANTISI ---
    try:
        s3_client, s3_prefix = get_s3_prefix_and_client(scan.id)
        scan.output_directory = s3_prefix 
        scan.save()
    except Exception as e:
        logging.error(f"[-] S3 İstemcisi oluşturulurken hata: {e}.")
        scan.status = 'FAILED'
        scan.save()
        return
    # --- DEĞİŞİKLİK SONU ---

    domain_input = scan.target_full_domain
    clean_domain = get_clean_domain(domain_input)
    internal_ip_range = scan.internal_ip_range
    apk_file_path = scan.apk_file_s3_path
    
    aws_keys = {}
    if scan.aws_access_key:
        aws_keys['access_key'] = scan.aws_access_key
        aws_keys['secret_key'] = scan.aws_secret_key
        aws_keys['region'] = scan.aws_region

    # Gemini API anahtarını sabit kodlamak yerine settings'den al
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logging.error("[-] Gemini API anahtarı settings.py (AWS Secrets Manager) içinde ayarlanmamış!")
        scan.status = 'FAILED'
        scan.save()
        return
        
    image_name = "pentest-araci-kali:v1.5"

    try:
        logging.info(f"\n[+] Scan ID {scan.id} için paralel görevler başlatılıyor...")
        
        # --- DEĞİŞİKLİK: Modüllere S3 argümanlarını yolluyoruz ---
        s3_args = (s3_client, settings.AWS_STORAGE_BUCKET_NAME, s3_prefix)
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(recon_module.run_reconnaissance, clean_domain, domain_input, image_name, *s3_args),
                executor.submit(web_app_module.run_web_tests, domain_input, image_name, *s3_args),
                executor.submit(api_module.run_api_tests, domain_input, image_name, *s3_args)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result()
        
        logging.info("\n[+] Paralel görevler tamamlandı.")
        
        if internal_ip_range:
            internal_network_module.run_internal_tests(internal_ip_range, image_name, *s3_args)
        if aws_keys:
            cloud_module.run_cloud_tests(
                aws_keys['access_key'], aws_keys['secret_key'], aws_keys['region'],
                image_name, *s3_args
            )
        # ... (Diğer modüller buraya eklenebilir) ...

    except Exception as e:
        logging.exception(f"[-] Scan ID {scan.id} testler sırasında çöktü: {e}")
        scan.status = 'FAILED'
        scan.save()
        return

    # --- Raporlama (S3 ile çalışacak şekilde) ---
    try:
        logging.info(f"\n[+] Scan ID {scan.id} için rapor oluşturuluyor...")
        scan.status = 'REPORTING'
        scan.save()
        
        report_file_s3_key = report_module.generate_report(
            s3_client, 
            settings.AWS_STORAGE_BUCKET_NAME, 
            s3_prefix, 
            domain_input, 
            api_key
        )
        
        if report_file_s3_key:
            scan.report_file_path = report_file_s3_key
            scan.status = 'COMPLETED'
            logging.info(f"\n[+] Scan ID {scan.id} tamamlandı. Rapor S3'e yüklendi: {scan.report_file_path}")
        else:
            logging.error(f"[-] Rapor oluşturma başarısız oldu, S3 anahtarı alınamadı.")
            scan.status = 'FAILED'
    
    except Exception as e:
        logging.exception(f"[-] Scan ID {scan.id} raporlama sırasında çöktü: {e}")
        scan.status = 'FAILED'

    scan.completed_at = datetime.now()
    scan.save()