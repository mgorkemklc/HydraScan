import os
import logging
import socket
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        return f"http://{target}"
    return target

def is_port_open(domain, port):
    """Port kontrolü yapar, kapalıysa aracı boşuna çalıştırmaz."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((domain, port))
        sock.close()
        return result == 0
    except:
        return False

def run_web_tests(domain_input, output_dir, image_name, selected_tools=[], stream_callback=None, custom_wordlist=None):
    logging.info("\n[+] Web Zafiyet Modülü Başlatılıyor...")
    if stream_callback: stream_callback("\n=== [3. WEB ZAFİYET MODÜLÜ] ===\n")

    target_url = ensure_http(domain_input)
    domain_only = target_url.replace("http://", "").replace("https://", "").split("/")[0]

    # Wordlist Ayarı
    wordlist_path_in_docker = "/usr/share/wordlists/dirb/common.txt"
    extra_docker_args = []
    
    if custom_wordlist and os.path.exists(custom_wordlist):
        wl_dir = os.path.dirname(custom_wordlist)
        wl_filename = os.path.basename(custom_wordlist)
        extra_docker_args = ['-v', f'{os.path.abspath(wl_dir)}:/wordlists']
        wordlist_path_in_docker = f"/wordlists/{wl_filename}"
        if stream_callback: stream_callback(f"[i] Özel Wordlist: {wl_filename}\n")

    commands = {}

    # --- DÜZELTİLMİŞ KOMUTLAR ---

    if "gobuster" in selected_tools:
        # DÜZELTME: -wildcard silindi, -k eklendi (SSL hatasını önler)
        commands["gobuster_ciktisi.txt"] = f"gobuster dir -u {target_url} -w {wordlist_path_in_docker} -q -b 301,302 -k --timeout 10s"

    if "nikto" in selected_tools:
        commands["nikto_ciktisi.txt"] = f"nikto -h {target_url} -maxtime 10m"

    if "nuclei" in selected_tools:
        commands["nuclei_ciktisi.txt"] = f"nuclei -u {target_url} -severity critical,high -timeout 5"

    if "sqlmap" in selected_tools:
        # DÜZELTME: --delay 2 ve --random-agent (Banlanmayı zorlaştırır)
        commands["sqlmap_ciktisi.txt"] = f"sqlmap -u \"{target_url}\" --batch --random-agent --level=1 --delay=2 --timeout=15"

    if "dalfox" in selected_tools:
        commands["dalfox_ciktisi.txt"] = f"dalfox url \"{target_url}\" --format plain --timeout 10"

    if "commix" in selected_tools:
        # DÜZELTME: Hata veren --crawl parametresi silindi.
        commands["commix_ciktisi.txt"] = f"commix -u {target_url} --batch --level=1 --disable-coloring"

    if "wapiti" in selected_tools:
        # Timeout koruması
        commands["wapiti_ciktisi.txt"] = f"timeout 10m wapiti -u {target_url} --flush-session -v 1 --max-scan-time 600 --depth 2 --scope folder"
    
    if "hydra" in selected_tools:
        # DÜZELTME: Port 22 kapalıysa hiç çalıştırma
        if is_port_open(domain_only, 22):
            commands["hydra_ciktisi.txt"] = f"hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{domain_only} -t 4 -I -f -W 1"
        else:
            msg = f"[-] Hydra atlandı: {domain_only} üzerinde SSH portu (22) kapalı.\n"
            logging.info(msg)
            if stream_callback: stream_callback(msg)

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        tool_name = output_filename.split('_')[0].upper()
        
        logging.info(f"--> Çalıştırılıyor: {tool_name}...")
        if stream_callback: stream_callback(f"[*] {tool_name} çalışıyor...\n")
        
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_docker_args, stream_callback=stream_callback)

    if stream_callback: stream_callback("\n[+] Web Modülü Tamamlandı.\n")