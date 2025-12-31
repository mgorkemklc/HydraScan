import os
import logging
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        return f"http://{target}"
    return target

# Parametrelere stream_callback ve custom_wordlist eklendi
def run_web_tests(domain_input, output_dir, image_name, selected_tools=[], stream_callback=None, custom_wordlist=None):
    logging.info("\n[+] Web Zafiyet Modülü Başlatılıyor...")
    if stream_callback: stream_callback("\n=== [3. WEB ZAFİYET MODÜLÜ] ===\n")

    target_url = ensure_http(domain_input)
    
    # Wordlist Ayarı
    wordlist_path_in_docker = "/usr/share/wordlists/dirb/common.txt" # Varsayılan
    extra_docker_args = []
    
    # Eğer özel wordlist seçildiyse
    if custom_wordlist and os.path.exists(custom_wordlist):
        wl_dir = os.path.dirname(custom_wordlist)
        wl_filename = os.path.basename(custom_wordlist)
        # Klasörü /wordlists olarak bağla
        extra_docker_args = ['-v', f'{os.path.abspath(wl_dir)}:/wordlists']
        wordlist_path_in_docker = f"/wordlists/{wl_filename}"
        if stream_callback: stream_callback(f"[i] Özel Wordlist Kullanılıyor: {wl_filename}\n")

    commands = {}

    if "gobuster" in selected_tools:
        # Dinamik wordlist yolu
        commands["gobuster_ciktisi.txt"] = f"gobuster dir -u {target_url} -w {wordlist_path_in_docker} -q -b 301,302 --wildcard"

    if "nikto" in selected_tools:
        commands["nikto_ciktisi.txt"] = f"nikto -h {target_url}"

    if "nuclei" in selected_tools:
        commands["nuclei_ciktisi.txt"] = f"nuclei -u {target_url} -severity critical,high"

    if "sqlmap" in selected_tools:
        commands["sqlmap_ciktisi.txt"] = f"sqlmap -u \"{target_url}\" --batch --random-agent --level=1"

    if "dalfox" in selected_tools:
        commands["dalfox_ciktisi.txt"] = f"dalfox url \"{target_url}\" --format plain"

    if "commix" in selected_tools:
        commands["commix_ciktisi.txt"] = f"commix -u {target_url} --crawl=2 --batch"

    if "wapiti" in selected_tools:
        commands["wapiti_ciktisi.txt"] = f"wapiti -u {target_url} --flush-session -v 1"
    
    if "hydra" in selected_tools:
        domain_only = target_url.split("//")[-1].split("/")[0]
        commands["hydra_ciktisi.txt"] = f"hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{domain_only} -t 4 -I -f"

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        # stream_callback ve extra_docker_args'ı iletiyoruz
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_docker_args, stream_callback=stream_callback)

    if stream_callback: stream_callback("\n[+] Web Modülü Tamamlandı.\n")