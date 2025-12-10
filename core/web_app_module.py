# core/web_app_module.py

import os
import logging
from core.docker_helper import run_command_in_docker

def ensure_protocol(target):
    """
    Hedefin başında http:// veya https:// yoksa http:// ekler.
    """
    target = target.strip()
    if not (target.startswith("http://") or target.startswith("https://")):
        return f"http://{target}"
    return target

def run_web_tests(domain_input, image_name, output_dir):
    """
    Web uygulama test araçlarını çalıştırır. URL formatını düzeltir.
    """
    logging.info("\n[+] 3. Web Uygulama Zafiyet Analizi modülü başlatılıyor...")

    # Hedefi tam URL formatına getir
    target_url = ensure_protocol(domain_input) # Örn: http://www.site.com

    commands = {
        # Artık komutların içinde manuel 'http://' yok, target_url'den geliyor.
        "gobuster_ciktisi.txt": f"gobuster dir -u {target_url} -w /usr/share/wordlists/dirb/common.txt -q -fw",
        "sqlmap_ciktisi.txt": f"sqlmap -u \"{target_url}\" --batch --level=1 --risk=1",
        "dalfox_ciktisi.txt": f"dalfox url \"{target_url}\"",
        "commix_ciktisi.txt": f"commix -u \"{target_url}\" --batch"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Web Uygulama Zafiyet Analizi modülü tamamlandı.")