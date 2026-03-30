import os
import logging
from core.docker_helper import run_command_in_docker

def run_internal_tests(ip_range, output_dir, image_name="pentest-araci-kali:v1.5", selected_tools=[], stream_callback=None):
    logging.info(f"\n[+] İç Ağ Zafiyet Analizi başlatılıyor. Hedef: {ip_range}")
    if stream_callback: stream_callback(f"[+] İç Ağ Analizi başlatıldı. Hedef: {ip_range}\n")

    os.makedirs(output_dir, exist_ok=True)
    commands = {}

    # --- Hızlı Keşif ---
    if "masscan" in selected_tools:
        commands["masscan_ciktisi.txt"] = f"timeout 10m masscan -p1-65535,U:1-65535 {ip_range} --rate=1000"
    if "nmap" in selected_tools:
        commands["nmap_ciktisi.txt"] = f"timeout 15m nmap -sV -sC -p- -T4 {ip_range}"
        
    # --- Active Directory ve SMB Analizi ---
    if "netexec" in selected_tools:
        commands["netexec_ciktisi.txt"] = f"timeout 10m nxc smb {ip_range} --gen-relay-list"
    if "enum4linux" in selected_tools:
        commands["enum4linux_ciktisi.txt"] = f"timeout 10m enum4linux -a {ip_range}"

    # --- Dinleme ve Sömürü ---
    if "responder" in selected_tools:
        # Responder sürekli dinleme yaptığı için kesin timeout veriyoruz
        commands["responder_ciktisi.txt"] = f"timeout 5m responder -I eth0 -rdww"
    if "hydra" in selected_tools:
        # Örnek SSH brute-force (Gerçek senaryoda port tespiti sonrası çalıştırılmalı)
        commands["hydra_ciktisi.txt"] = f"timeout 15m hydra -L /usr/share/wordlists/rockyou.txt -P /usr/share/wordlists/rockyou.txt ssh://{ip_range} -t 4"

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        tool_name = output_filename.split('_')[0].upper()

        if stream_callback: stream_callback(f"[*] {tool_name} çalıştırılıyor...")
        logging.info(f"--> Çalıştırılıyor: {tool_name}...")

        run_command_in_docker(command, output_file_path, image_name, stream_callback=stream_callback)

        if stream_callback: stream_callback(f"[+] {tool_name} tamamlandı.")

    if stream_callback: stream_callback("\n[√] Tüm İç Ağ Modülü işlemleri başarıyla tamamlandı.")
    return True