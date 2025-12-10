# core/recon_module.py

import os
import logging
from urllib.parse import urlparse
from core.docker_helper import run_command_in_docker

def get_clean_domain(input_target):
    """
    Girdiden protokolü (http://) ve path'i (/) temizler, sadece domaini bırakır.
    Örn: https://www.site.com/login -> www.site.com
    """
    target = input_target.strip()
    if not target.startswith("http"):
        target = "http://" + target
    
    parsed = urlparse(target)
    return parsed.netloc

def get_root_domain(domain):
    """
    Subdomainleri temizleyip kök domaini bulmaya çalışır.
    Örn: www.site.com -> site.com
    (Basit split mantığı, karmaşık TLD'ler için tldextract eklenebilir ama şimdilik bu yeterli)
    """
    parts = domain.split('.')
    if len(parts) > 2:
        return ".".join(parts[-2:]) # son iki parçayı al
    return domain

def run_reconnaissance(domain_input, full_domain_input, image_name, output_dir):
    """
    Keşif araçlarını çalıştırır. Girdiyi her araç için uygun formata sokar.
    """
    logging.info("\n[+] 2. Keşif ve Saldırı Yüzeyi Haritalama modülü başlatılıyor...")

    # Girdileri temizle
    clean_domain = get_clean_domain(domain_input) # www.site.com
    root_domain = get_root_domain(clean_domain)   # site.com

    commands = {
        # Whois ve Subfinder genellikle kök domain ister
        "whois_ciktisi.txt": f"whois {root_domain}",
        "subfinder_ciktisi.txt": f"subfinder -d {root_domain}",
        
        # Dig ve Nmap, verilen spesifik domaini (subdomain dahil) taramalı
        "dig_ciktisi.txt": f"dig {clean_domain} ANY",
        "nmap_ciktisi.txt": f"nmap -sV -T4 {clean_domain}",
        
        # Nikto tam URL ister
        "nikto_ciktisi.txt": f"nikto -h http://{clean_domain} -Tuning 1,2,3,4,5"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Keşif modülü tamamlandı.")