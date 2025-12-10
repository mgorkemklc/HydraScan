# core/web_app_module.py

import os
import logging
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    """
    URL'nin başında http/https yoksa ekler.
    Commix, SQLMap gibi araçlar protokolü bilmek zorundadır.
    """
    target = target.strip()
    if not (target.startswith("http://") or target.startswith("https://")):
        return f"http://{target}"
    return target

def run_web_tests(domain_input, output_dir, image_name, selected_tools=[]):
    logging.info("\n[+] 3. Web Zafiyet Modülü Başlatılıyor...")

    # Hedefi tam URL formatına getir (http://www.site.com)
    target_url = ensure_http(domain_input)

    commands = {}

    if "gobuster" in selected_tools:
        # HATA DÜZELTİLDİ: -fw parametresi kaldırıldı.
        commands["gobuster_ciktisi.txt"] = f"gobuster dir -u {target_url} -w /usr/share/wordlists/dirb/common.txt -q"

    if "nikto" in selected_tools:
        commands["nikto_ciktisi.txt"] = f"nikto -h {target_url} -Tuning 1,2,3"

    if "nuclei" in selected_tools:
        commands["nuclei_ciktisi.txt"] = f"nuclei -u {target_url} -t cves/ -severity critical,high"

    if "sqlmap" in selected_tools:
        # URL tırnak içine alındı
        commands["sqlmap_ciktisi.txt"] = f"sqlmap -u \"{target_url}\" --batch --dbs --random-agent --level=1 --risk=1"

    if "dalfox" in selected_tools:
        commands["dalfox_ciktisi.txt"] = f"dalfox url \"{target_url}\" --format plain"

    if "commix" in selected_tools:
        # HATA DÜZELTİLDİ: URL tırnak içine alındı, çift http engellendi.
        commands["commix_ciktisi.txt"] = f"commix -u \"{target_url}\" --batch"

    if "wapiti" in selected_tools:
        commands["wapiti_ciktisi.txt"] = f"wapiti -u {target_url} --flush-session -v 1"
    
    if "hydra" in selected_tools:
        # Hydra genelde IP/Domain ister, URL'den domaini ayıklıyoruz
        domain_only = target_url.split("//")[-1].split("/")[0]
        # Örnek SSH saldırısı (Dikkat: Sadece izinli sistemlerde kullanın)
        commands["hydra_ciktisi.txt"] = f"hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{domain_only} -t 4 -f -I"

    for output_filename, command in commands.items():
        logging.info(f"[*] Çalıştırılıyor: {command.split()[0]}")
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Web Zafiyet modülü tamamlandı.")