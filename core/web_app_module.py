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
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((domain, port))
        sock.close()
        return result == 0
    except:
        return False

def run_web_tests(domain_input, output_dir, image_name="pentest-araci-kali:v1.5", selected_tools=[], stream_callback=None, custom_wordlist=None):
    logging.info("\n[+] Web Zafiyet Modülü Başlatılıyor...")
    
    target_url = ensure_http(domain_input)
    domain_only = target_url.replace("http://", "").replace("https://", "").split("/")[0]

    os.makedirs(output_dir, exist_ok=True)

    wordlist_path_in_docker = "/usr/share/wordlists/dirb/common.txt"
    extra_docker_args = []
    
    if custom_wordlist and os.path.exists(custom_wordlist):
        wl_dir = os.path.dirname(custom_wordlist)
        wl_filename = os.path.basename(custom_wordlist)
        extra_docker_args = ['-v', f'{os.path.abspath(wl_dir)}:/wordlists']
        wordlist_path_in_docker = f"/wordlists/{wl_filename}"
        if stream_callback: stream_callback(f"[i] Özel Wordlist Kullanılıyor: {wl_filename}")

    commands = {}

    # --- Keşif ve Fuzzing ---
    if "gobuster" in selected_tools:
        commands["gobuster_ciktisi.txt"] = f"timeout 15m gobuster dir -u {target_url} -w {wordlist_path_in_docker} -q -b 301,302 -k --timeout 10s"
    if "ffuf" in selected_tools:
        commands["ffuf_ciktisi.txt"] = f"timeout 15m ffuf -u {target_url}/FUZZ -w {wordlist_path_in_docker} -t 50 -mc 200,204,301,302,307,401,403"
    if "dirsearch" in selected_tools:
        commands["dirsearch_ciktisi.txt"] = f"timeout 15m dirsearch -u {target_url} -e php,html,js -x 400,404,500,503 --format=plain"
    if "amass" in selected_tools:
        commands["amass_ciktisi.txt"] = f"timeout 10m amass enum -passive -d {domain_only}"
    if "subfinder" in selected_tools:
        commands["subfinder_ciktisi.txt"] = f"subfinder -d {domain_only} -silent"

    # --- Zafiyet Tarama ---
    if "nuclei" in selected_tools:
        commands["nuclei_ciktisi.txt"] = f"nuclei -u {target_url} -severity critical,high,medium -timeout 5"
    if "nikto" in selected_tools:
        commands["nikto_ciktisi.txt"] = f"timeout 15m nikto -h {target_url} -maxtime 10m"
    if "wapiti" in selected_tools:
        commands["wapiti_ciktisi.txt"] = f"timeout 10m wapiti -u {target_url} --flush-session -v 1 --max-scan-time 600"
    if "wpscan" in selected_tools:
        commands["wpscan_ciktisi.txt"] = f"timeout 15m wpscan --url {target_url} --enumerate u,p,t,vp,vt --random-user-agent --disable-tls-checks"

    # --- Exploitation (Sömürü) ---
    if "sqlmap" in selected_tools:
        commands["sqlmap_ciktisi.txt"] = f"timeout 15m sqlmap -u \"{target_url}\" --batch --random-agent --level=2 --risk=2 --delay=1 --timeout=15"
    if "dalfox" in selected_tools:
        commands["dalfox_ciktisi.txt"] = f"timeout 10m dalfox url \"{target_url}\" --format plain --timeout 10"
    if "xsstrike" in selected_tools:
        commands["xsstrike_ciktisi.txt"] = f"timeout 10m python3 /opt/XSStrike/xsstrike.py -u \"{target_url}\" --crawl -l 3"
    if "commix" in selected_tools:
        commands["commix_ciktisi.txt"] = f"timeout 10m commix -u \"{target_url}\" --batch --level=1 --disable-coloring"

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        tool_name = output_filename.split('_')[0].upper()
        
        if stream_callback: stream_callback(f"\n[*] {tool_name} başlatıldı...")
        logging.info(f"--> Çalıştırılıyor: {tool_name}...")
        
        # Docker komutunu çalıştır
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_docker_args, stream_callback=stream_callback)
        
        if stream_callback: stream_callback(f"[+] {tool_name} tamamlandı.")

    if stream_callback: stream_callback("\n[√] Tüm Web Modülü işlemleri başarıyla tamamlandı.")
    return True