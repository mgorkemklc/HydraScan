# core/web_app_module.py (YENİ - YEREL HALİ)

import os
import logging
# Importu düzeltelim
from core.docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 's3_client', 'bucket_name', 's3_prefix' parametreleri
# 'output_dir' ile değişti.
def run_web_tests(domain, image_name, output_dir):
    """
    Web uygulama test araçlarını çalıştırır ve çıktıları yerel output_dir içine kaydeder.
    """
    logging.info("\n[+] 3. Web Uygulama Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        "gobuster_ciktisi.txt": f"gobuster dir -u http://{domain} -w /usr/share/wordlists/dirb/common.txt -q",
        "sqlmap_ciktisi.txt": f"sqlmap -u http://{domain} --batch --level=1 --risk=1",
        "dalfox_ciktisi.txt": f"dalfox url http://{domain} --batch",
        "commix_ciktisi.txt": f"commix -u http://{domain} --batch"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Tam dosya yolu oluşturuyoruz
        output_file_path = os.path.join(output_dir, output_filename)
        
        # docker_helper'a yerel dosya yolunu iletiyoruz
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Web Uygulama Zafiyet Analizi modülü tamamlandı.")