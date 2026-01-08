import os
import logging
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")): return f"http://{target}"
    return target

def run_web_tests(domain_input, output_dir, image_name, selected_tools=[], stream_callback=None, custom_wordlist=None):
    logging.info("\n[+] Web Zafiyet Modülü Başlatılıyor...")
    if stream_callback: stream_callback("\n=== [3. WEB ZAFİYET MODÜLÜ] ===\n")

    target_url = ensure_http(domain_input)
    wordlist_path = "/usr/share/wordlists/dirb/common.txt"
    extra_args = []
    
    if custom_wordlist and os.path.exists(custom_wordlist):
        wl_dir = os.path.dirname(custom_wordlist)
        wl_name = os.path.basename(custom_wordlist)
        extra_args = ['-v', f'{os.path.abspath(wl_dir)}:/wordlists']
        wordlist_path = f"/wordlists/{wl_name}"
        if stream_callback: stream_callback(f"[i] Özel Wordlist: {wl_name}\n")

    commands = {}

    # TIMEOUT EKLENMİŞ KOMUTLAR
    if "gobuster" in selected_tools:
        commands["gobuster_ciktisi.txt"] = f"gobuster dir -u {target_url} -w {wordlist_path} -q -b 301,302 --wildcard --timeout 10s"
    if "nikto" in selected_tools:
        commands["nikto_ciktisi.txt"] = f"nikto -h {target_url} -maxtime 10m"
    if "nuclei" in selected_tools:
        commands["nuclei_ciktisi.txt"] = f"nuclei -u {target_url} -severity critical,high -timeout 5"
    if "sqlmap" in selected_tools:
        commands["sqlmap_ciktisi.txt"] = f"sqlmap -u \"{target_url}\" --batch --random-agent --level=1 --timeout=10"
    if "dalfox" in selected_tools:
        commands["dalfox_ciktisi.txt"] = f"dalfox url \"{target_url}\" --format plain --timeout 10"
    if "commix" in selected_tools:
        commands["commix_ciktisi.txt"] = f"commix -u {target_url} --crawl=2 --batch"
    
    # KRİTİK WAPITI AYARI
    if "wapiti" in selected_tools:
        commands["wapiti_ciktisi.txt"] = f"timeout 10m wapiti -u {target_url} --flush-session -v 1 --max-scan-time 600 --depth 2 --scope folder"
    
    if "hydra" in selected_tools:
        domain_only = target_url.split("//")[-1].split("/")[0]
        commands["hydra_ciktisi.txt"] = f"hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{domain_only} -t 4 -I -f -W 1"

    for fname, cmd in commands.items():
        out_path = os.path.join(output_dir, fname)
        logging.info(f"--> Çalıştırılıyor: {fname.split('_')[0].upper()}...")
        if stream_callback: stream_callback(f"[*] {fname.split('_')[0].upper()} çalışıyor...\n")
        run_command_in_docker(cmd, out_path, image_name, extra_docker_args=extra_args, stream_callback=stream_callback)

    if stream_callback: stream_callback("\n[+] Web Modülü Tamamlandı.\n")