# core/recon_module.py (YENİ - YEREL HALİ)

import os
import logging
# .docker_helper'daki importu projenin ana klasöründen 
# çalıştığımızı varsayarak düzeltiyoruz.
# Eğer 'core' içinden çalıştırırsak .docker_helper kalmalı.
# Şimdilik app.py'den çağıracağımız için 'core.' kullanacağız.
from core.docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 's3_client', 'bucket_name', 's3_prefix' parametreleri
# 'output_dir' (örn: "C:\\...\\scan_outputs\\scan_1") ile değişti.
def run_reconnaissance(domain, full_domain, image_name, output_dir):
    """
    Keşif araçlarını çalıştırır ve çıktıları yerel output_dir içine kaydeder.
    """
    logging.info("\n[+] 2. Keşif ve Saldırı Yüzeyi Haritalama modülü başlatılıyor...")

    commands = {
        "whois_ciktisi.txt": f"whois {domain}",
        "dig_ciktisi.txt": f"dig {domain} ANY",
        "subfinder_ciktisi.txt": f"subfinder -d {domain}",
        "nmap_ciktisi.txt": f"nmap -sV -T4 {domain}",
        # Nikto komutunu /output klasörüne yazacak şekilde güncelleyelim
        "nikto_ciktisi.txt": f"nikto -h http://{full_domain} -Tuning 1,2,3,4,5"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık S3 anahtarı değil, tam dosya yolu oluşturuyoruz
        output_file_path = os.path.join(output_dir, output_filename)
        
        # docker_helper'a S3 bilgileri yerine yerel dosya yolunu iletiyoruz
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Keşif ve Saldırı Yüzeyi Haritalama modülü tamamlandı.")