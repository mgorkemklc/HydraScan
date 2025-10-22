import os
import logging
from .docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 'output_dir' parametresi S3 argümanlarıyla değişti
def run_internal_tests(ip_range, image_name, s3_client, bucket_name, s3_prefix):
    """
    İç ağ test araçlarını çalıştırır ve çıktıları S3'e yükler.
    """
    logging.info("\n[+] 5. İç Ağ Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        "responder_analizi.txt": "echo 'Responder analizi (manuel olarak çalıştırılmalı) bu IP aralığı için planlandı: {ip_range}'",
        "nmap_ic_ag_ciktisi.txt": f"nmap -T4 -F {ip_range}"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık yerel yol değil, S3 anahtarı (yolu) oluşturuyoruz
        s3_key = f"{s3_prefix}{output_filename}"
        
        # docker_helper'a S3 bilgilerini iletiyoruz
        run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name)

    logging.info("\n[+] İç Ağ Zafiyet Analizi modülü tamamlandı.")