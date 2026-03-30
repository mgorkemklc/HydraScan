import os
import logging
import socket
import concurrent.futures
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        return f"http://{target}"
    return target

def run_web_tests(domain_input, output_dir, image_name="pentest-araci-kali:v1.5", selected_tools=[], stream_queue=None, custom_wordlist=None):
    if stream_queue: stream_queue.put("\n[+] Paralel Web Zafiyet Modülü Başlatılıyor...")
    target_url = ensure_http(domain_input)
    domain_only = target_url.replace("http://", "").replace("https://", "").split("/")[0]
    os.makedirs(output_dir, exist_ok=True)

    wordlist_arg = "/usr/share/wordlists/dirb/common.txt"
    extra_args = []
    if custom_wordlist and os.path.exists(custom_wordlist):
        extra_args = ['-v', f'{os.path.dirname(custom_wordlist)}:/wordlists']
        wordlist_arg = f"/wordlists/{os.path.basename(custom_wordlist)}"

    commands = {}
    if "gobuster" in selected_tools: commands["gobuster_ciktisi.txt"] = f"timeout 15m gobuster dir -u {target_url} -w {wordlist_arg} -q -b 301,302 -k --timeout 10s"
    if "ffuf" in selected_tools: commands["ffuf_ciktisi.txt"] = f"timeout 15m ffuf -u {target_url}/FUZZ -w {wordlist_arg} -t 50 -mc 200,204,301,302,307,401,403"
    if "dirsearch" in selected_tools: commands["dirsearch_ciktisi.txt"] = f"timeout 15m dirsearch -u {target_url} -e php,html,js -x 400,404,500,503 --format=plain"
    if "nuclei" in selected_tools: commands["nuclei_ciktisi.txt"] = f"timeout 15m nuclei -u {target_url} -severity critical,high,medium -timeout 5 -j -o /app/output/nuclei_ciktisi.json"
    if "wapiti" in selected_tools: commands["wapiti_ciktisi.txt"] = f"timeout 10m wapiti -u {target_url} --flush-session -v 1 --max-scan-time 600"
    if "sqlmap" in selected_tools: commands["sqlmap_ciktisi.txt"] = f"timeout 15m sqlmap -u \"{target_url}\" --batch --random-agent --level=2 --risk=2 --delay=1"
    if "dalfox" in selected_tools: commands["dalfox_ciktisi.txt"] = f"timeout 10m dalfox url \"{target_url}\" --format plain --timeout 10"
    if "wpscan" in selected_tools: commands["wpscan_ciktisi.txt"] = f"timeout 15m wpscan --url {target_url} --enumerate u,p,t,vp,vt --random-user-agent --disable-tls-checks"
    if "xsstrike" in selected_tools: commands["xsstrike_ciktisi.txt"] = f"timeout 10m python3 /opt/XSStrike/xsstrike.py -u \"{target_url}\" --crawl -l 3"
    if "commix" in selected_tools: commands["commix_ciktisi.txt"] = f"timeout 10m commix -u \"{target_url}\" --batch --level=1 --disable-coloring"

    # Eşzamanlı (Paralel) Tarama Fonksiyonu
    def execute_tool(output_filename, command):
        tool_name = output_filename.split('_')[0].upper()
        if stream_queue: stream_queue.put(f"[*] {tool_name} motoru ateşlendi...")
        output_file_path = os.path.join(output_dir, output_filename)
        
        # Logları doğrudan queue'ya gönderen lambda
        def queue_callback(msg):
            if stream_queue: stream_queue.put(msg)
            
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_args, stream_callback=queue_callback)
        if stream_queue: stream_queue.put(f"[+] {tool_name} analizi tamamlandı.")

    # 3 Aracı Aynı Anda Çalıştırır (Süreyi 3 kat kısaltır)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(execute_tool, fname, cmd) for fname, cmd in commands.items()]
        concurrent.futures.wait(futures)

    if stream_queue: stream_queue.put("\n[√] Tüm Web Modülü işlemleri başarıyla tamamlandı.")
    return True