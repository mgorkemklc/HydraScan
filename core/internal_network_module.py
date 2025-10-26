# core/internal_network_module.py (YENİ - YEREL HALİ)

import os
import logging
# Importu düzeltelim
from core.docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 's3_client', 'bucket_name', 's3_prefix' parametreleri
# 'output_dir' ile değişti.
def run_internal_tests(ip_range, image_name, output_dir):
    """
    İç ağ test araçlarını çalıştırır ve çıktıları yerel output_dir içine kaydeder.
    """
    logging.info("\n[+] 5. İç Ağ Zafiyet Analizi modülü başlatılıyor...")

    commands = {
        # Responder çıktısını dosyaya yazmak yerine not düşelim
        "responder_analizi.txt": f"echo 'Responder analizi (manuel olarak çalıştırılmalı) bu IP aralığı için planlandı: {ip_range}'",
        "nmap_ic_ag_ciktisi.txt": f"nmap -T4 -F {ip_range}"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Tam dosya yolu oluşturuyoruz
        output_file_path = os.path.join(output_dir, output_filename)
        
        # docker_helper'a yerel dosya yolunu iletiyoruz
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] İç Ağ Zafiyet Analizi modülü tamamlandı.")