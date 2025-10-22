import os
import logging
from .docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 'output_dir' parametresi S3 argümanlarıyla değişti
def run_web_tests(domain, image_name, s3_client, bucket_name, s3_prefix):
    """
    Web uygulama test araçlarını çalıştırır ve çıktıları S3'e yükler.
    """
    logging.info("\n[+] 3. Web Uygulama Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        "gobuster_ciktisi.txt": f"gobuster dir -u http://{domain} -w /usr/share/wordlists/dirb/common.txt -q",
        "sqlmap_ciktisi.txt": f"sqlmap -u http://{domain} --batch --level=1 --risk=1",
        "dalfox_ciktisi.txt": f"dalfox url http://{domain} --batch",
        "commix_ciktisi.txt": f"commix -u http://{domain} --batch"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık yerel yol değil, S3 anahtarı (yolu) oluşturuyoruz
        s3_key = f"{s3_prefix}{output_filename}"
        
        # docker_helper'a S3 bilgilerini iletiyoruz
        run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name)

    logging.info("\n[+] Web Uygulama Zafiyet Analizi modülü tamamlandı.")