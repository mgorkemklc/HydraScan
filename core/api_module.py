import os
import logging
from .docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 'output_dir' parametresi S3 argümanlarıyla değişti
def run_api_tests(domain, image_name, s3_client, bucket_name, s3_prefix):
    """
    API test araçlarını çalıştırır ve çıktıları S3'e yükler.
    """
    logging.info("\n[+] 4. API Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        "kiterunner_ciktisi.txt": f"kiterunner scan http://{domain}/ -w /usr/share/wordlists/dirb/common.txt --ignore-status=404,400,500"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık yerel yol değil, S3 anahtarı (yolu) oluşturuyoruz
        s3_key = f"{s3_prefix}{output_filename}"
        
        # docker_helper'a S3 bilgilerini iletiyoruz
        run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name)

    logging.info("\n[+] API Zafiyet Analizi modülü tamamlandı.")