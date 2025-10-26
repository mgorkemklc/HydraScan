# core/api_module.py (YENİ - YEREL HALİ)

import os
import logging
# Importu düzeltelim
from core.docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 's3_client', 'bucket_name', 's3_prefix' parametreleri
# 'output_dir' ile değişti.
def run_api_tests(domain, image_name, output_dir):
    """
    API test araçlarını çalıştırır ve çıktıları yerel output_dir içine kaydeder.
    """
    logging.info("\n[+] 4. API Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        # Kiterunner'ın çıktısını /output klasörüne yönlendirelim
        "kiterunner_ciktisi.txt": f"kiterunner scan http://{domain}/ -w /usr/share/wordlists/dirb/common.txt --ignore-status=404,400,500"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Tam dosya yolu oluşturuyoruz
        output_file_path = os.path.join(output_dir, output_filename)
        
        # docker_helper'a yerel dosya yolunu iletiyoruz
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] API Zafiyet Analizi modülü tamamlandı.")