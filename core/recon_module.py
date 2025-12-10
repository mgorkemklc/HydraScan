# core/recon_module.py

import os
import logging
from urllib.parse import urlparse
from core.docker_helper import run_command_in_docker

def get_clean_domain(input_target):
    """
    Girdiden protokolü (http://) temizler.
    Örn: https://www.site.com -> www.site.com
    """
    target = input_target.strip()
    if target.startswith("http://") or target.startswith("https://"):
        parsed = urlparse(target)
        return parsed.netloc
    return target

def get_root_domain(domain):
    """
    Alt domainleri temizleyip kök domaini bulur.
    Örn: www.site.com -> site.com
    """
    parts = domain.split('.')
    if len(parts) > 2:
        return ".".join(parts[-2:]) # Son iki parçayı al
    return domain

def run_reconnaissance(domain_input, output_dir, image_name, selected_tools=[]):
    logging.info("\n[+] 2. Keşif Modülü Başlatılıyor...")

    # Girdileri temizle ve hazırla
    clean_domain = get_clean_domain(domain_input) # www.site.com (Nmap, Dig için)
    root_domain = get_root_domain(clean_domain)   # site.com (Whois, Subfinder için)

    commands = {}

    # Whois ve Subfinder KÖK domain ister
    if "whois" in selected_tools:
        commands["whois_ciktisi.txt"] = f"whois {root_domain}"
    
    if "subfinder" in selected_tools:
        commands["subfinder_ciktisi.txt"] = f"subfinder -d {root_domain}"
    
    if "amass" in selected_tools:
        commands["amass_ciktisi.txt"] = f"amass enum -passive -d {root_domain}"

    # Dig ve Nmap tam domain (subdomain dahil) ister
    if "dig" in selected_tools:
        commands["dig_ciktisi.txt"] = f"dig {clean_domain} ANY"

    if "nmap" in selected_tools:
        commands["nmap_ciktisi.txt"] = f"nmap -sV -F --open {clean_domain}"

    for output_filename, command in commands.items():
        logging.info(f"[*] Çalıştırılıyor: {command.split()[0]}")
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    logging.info("\n[+] Keşif modülü tamamlandı.")