import os
import logging
from core.docker_helper import run_command_in_docker

def run_reconnaissance(domain_input, output_dir, image_name, selected_tools=[], stream_callback=None):
    logging.info("\n[+] 2. Keşif Modülü Başlatılıyor...")
    if stream_callback: stream_callback("\n=== [2. KEŞİF MODÜLÜ] ===\n")

    clean_domain = domain_input.replace("http://", "").replace("https://", "").split("/")[0]
    
    commands = {}

    if "whois" in selected_tools:
        commands["whois_ciktisi.txt"] = f"whois {clean_domain}"

    if "subfinder" in selected_tools:
        commands["subfinder_ciktisi.txt"] = f"subfinder -d {clean_domain}"

    if "amass" in selected_tools:
        # DÜZELTME: Sadece pasif tarama, timeout ve basit komut.
        commands["amass_ciktisi.txt"] = f"amass enum -passive -d {clean_domain} -timeout 5"

    if "dig" in selected_tools:
        commands["dig_ciktisi.txt"] = f"dig {clean_domain} ANY"

    if "nmap" in selected_tools:
        commands["nmap_ciktisi.txt"] = f"nmap -sV -F --open {clean_domain}"

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        tool_name = output_filename.split('_')[0].upper()
        
        logging.info(f"[*] Çalıştırılıyor: {tool_name}")
        if stream_callback: stream_callback(f"[*] {tool_name} çalışıyor...\n")
        
        run_command_in_docker(command, output_file_path, image_name, stream_callback=stream_callback)

    if stream_callback: stream_callback("\n[+] Keşif modülü tamamlandı.\n")