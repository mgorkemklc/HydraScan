import os
from .docker_helper import run_command_in_docker

def run_reconnaissance(domain, full_domain, output_dir, image_name):
    """
    Keşif ve saldırı yüzeyi haritalama araçlarını çalıştırır.
    """
    print("\n[+] 2. Keşif ve Saldırı Yüzeyi Haritalama modülü başlatılıyor...")

    commands = {
        "whois_ciktisi.txt": f"whois {domain}",
        "dig_ciktisi.txt": f"dig {domain} ANY",
        "subfinder_ciktisi.txt": f"subfinder -d {domain}",
        # DÜZELTME: Nmap artık tüm portları (-p-) tarayacak.
        "nmap_ciktisi.txt": f"nmap -sV -T4 {domain}",
        # Nikto'nun http://localhost:3000 gibi tam adrese ihtiyacı var
        "nikto_ciktisi.txt": f"nikto -h http://{full_domain} -Tuning 1,2,3,4,5"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    print("\n[+] Keşif ve Saldırı Yüzeyi Haritalama modülü tamamlandı.")