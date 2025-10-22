import os
import logging # print yerine logging
from .docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 'output_dir' parametresi S3 argümanlarıyla değişti
def run_reconnaissance(domain, full_domain, image_name, s3_client, bucket_name, s3_prefix):
    """
    Keşif ve saldırı yüzeyi haritalama araçlarını çalıştırır.
    """
    logging.info("\n[+] 2. Keşif ve Saldırı Yüzeyi Haritalama modülü başlatılıyor...")

    commands = {
        "whois_ciktisi.txt": f"whois {domain}",
        "dig_ciktisi.txt": f"dig {domain} ANY",
        "subfinder_ciktisi.txt": f"subfinder -d {domain}",
        "nmap_ciktisi.txt": f"nmap -sV -T4 {domain}",
        "nikto_ciktisi.txt": f"nikto -h http://{full_domain} -Tuning 1,2,3,4,5"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık yerel yol değil, S3 anahtarı (yolu) oluşturuyoruz
        s3_key = f"{s3_prefix}{output_filename}" 
        
        # docker_helper'a S3 bilgilerini iletiyoruz
        run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name)

    logging.info("\n[+] Keşif ve Saldırı Yüzeyi Haritalama modülü tamamlandı.")