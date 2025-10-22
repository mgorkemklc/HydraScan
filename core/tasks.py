# core/tasks.py

import os
import time
import logging
from celery import shared_task
from .models import Scan
from datetime import datetime

# --- YENİ IMPORTLAR (S3 İÇİN) ---
import boto3
from django.conf import settings
# --- IMPORTLAR SONU ---

# Kendi modüllerini "relative import" (from .) ile import et
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
    """
    S3'e bağlanır ve tarama için kullanılacak ana 'klasör' yolunu (prefix) döndürür.
    """
    # settings.py'deki AWS ayarlarını kullan
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    
    # S3'teki yol (klasör adı gibi düşün). 'media/' Django-storages için standarttır.
    s3_prefix = f"media/scan_outputs/{scan_id}/"
    
    return s3_client, s3_prefix

# --- ESKİ create_output_directory fonksiyonunu SİLDİK ---


def get_clean_domain(domain_with_port):
    """ 'localhost:3000' girdisinden 'localhost' döndürür. """
    if ':' in domain_with_port:
        return domain_with_port.split(':')[0]
    return domain_with_port


# --- ANA GÖREV (TAMAMEN DEĞİŞTİ) ---
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
    # Artık yerel klasör yok. S3 client ve S3 yolu (prefix) alınıyor.
    try:
        s3_client, s3_prefix = get_s3_prefix_and_client(scan.id)
        # Yolu (S3 prefix) veritabanına kaydedelim (örn: media/scan_outputs/1/)
        scan.output_directory = s3_prefix 
        scan.save()
    except Exception as e:
        logging.error(f"[-] S3 İstemcisi oluşturulurken hata: {e}. (settings.py'deki AWS ayarlarını kontrol et)")
        scan.status = 'FAILED'
        scan.save()
        return
    # --- DEĞİŞİKLİK SONU ---

    # Veritabanından değişkenleri al
    domain_input = scan.target_full_domain
    clean_domain = get_clean_domain(domain_input)
    internal_ip_range = scan.internal_ip_range
    apk_file_path = scan.apk_file_s3_path # (Bu da S3'e yüklenmeli, şimdilik null)
    
    # settings.py'deki AWS anahtarlarını al (cloud_module için)
    aws_keys = {}
    if scan.aws_access_key:
        aws_keys['access_key'] = scan.aws_access_key
        aws_keys['secret_key'] = scan.aws_secret_key
        aws_keys['region'] = scan.aws_region

    # Gemini API anahtarını güvenli bir yerden al (tasks.py'ye hardcode etmiştik)
    api_key = "SENIN-GERCEK-GEMINI-API-KEYIN-BURAYA-GELECEK"
    if not api_key:
        logging.error("[-] Gemini API anahtarı tasks.py içinde ayarlanmamış!")
        scan.status = 'FAILED'
        scan.save()
        return
        
    image_name = "pentest-araci-kali:v1.5" # Docker imaj adı

    try:
        logging.info(f"\n[+] Scan ID {scan.id} için paralel görevler başlatılıyor...")
        
        # --- DEĞİŞİKLİK: Modüllere S3 argümanlarını yolluyoruz ---
        # Artık 'absolute_output_dir' yollamıyoruz.
        s3_args = (s3_client, settings.AWS_STORAGE_BUCKET_NAME, s3_prefix)
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(recon_module.run_reconnaissance, clean_domain, domain_input, image_name, *s3_args),
                executor.submit(web_app_module.run_web_tests, domain_input, image_name, *s3_args),
                executor.submit(api_module.run_api_tests, domain_input, image_name, *s3_args)
            ]
            for future in concurrent.futures.as_completed(futures):
                future.result() # Hata varsa burada ortaya çıkar
        
        logging.info("\n[+] Paralel görevler tamamlandı.")
        
        if internal_ip_range:
            internal_network_module.run_internal_tests(internal_ip_range, image_name, *s3_args)
        if aws_keys:
            cloud_module.run_cloud_tests(
                aws_keys['access_key'], aws_keys['secret_key'], aws_keys['region'],
                image_name, *s3_args
            )
        if apk_file_path:
            # TODO: APK dosyasını S3'ten indirme mantığı buraya eklenmeli
            # mobile_module.run_mobile_tests(apk_file_path, image_name, *s3_args)
            logging.info("[i] Mobil tarama (S3'ten APK indirme) şimdilik atlandı.")

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
        
        # report_module'a S3 bilgilerini yolluyoruz
        report_file_s3_key = report_module.generate_report(
            s3_client, 
            settings.AWS_STORAGE_BUCKET_NAME, 
            s3_prefix, 
            domain_input, 
            api_key
        )
        
        if report_file_s3_key:
            # Raporun tam S3 yolunu (key) kaydet
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