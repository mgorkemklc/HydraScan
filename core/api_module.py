import os
import logging
from core.docker_helper import run_command_in_docker

def ensure_http(target):
    target = target.strip()
    if not target.startswith(("http://", "https://")):
        return f"http://{target}"
    return target

def run_api_tests(target_input, output_dir, image_name="pentest-araci-kali:v1.5", selected_tools=[], stream_callback=None, custom_wordlist=None):
    target_url = ensure_http(target_input)
    if stream_callback: stream_callback(f"\n[+] API Sızma Testi Başlatılıyor. Hedef: {target_url}")
    
    os.makedirs(output_dir, exist_ok=True)
    commands = {}

    # Özel wordlist (Swagger/OpenAPI yolları için) kullanımı
    wordlist_arg = "/usr/share/wordlists/dirb/common.txt" 
    extra_args = []
    
    if custom_wordlist and os.path.exists(custom_wordlist):
        wl_dir = os.path.dirname(custom_wordlist)
        wl_filename = os.path.basename(custom_wordlist)
        extra_args = ['-v', f'{os.path.abspath(wl_dir)}:/wordlists']
        wordlist_arg = f"/wordlists/{wl_filename}"

    # Araç komutları (API'yi yormamak için limitli sürelerle)
    if "kiterunner" in selected_tools:
        # Gerçek ortamda Kiterunner için kendi özel .kr wordlistleri kullanılmalıdır. Şimdilik metin bazlı fallback yapıyoruz.
        commands["kiterunner_ciktisi.txt"] = f"timeout 15m kr scan {target_url} -A=apiroutes-210228"
    if "nuclei" in selected_tools:
        # Nuclei'yi sadece API, GraphQL ve Swagger profilleriyle çalışmaya zorluyoruz
        commands["nuclei_ciktisi.txt"] = f"timeout 15m nuclei -u {target_url} -tags api,graphql,swagger -severity critical,high,medium"
    if "sqlmap" in selected_tools:
        commands["sqlmap_ciktisi.txt"] = f"timeout 15m sqlmap -u \"{target_url}\" --batch --level=2 --risk=2"
    if "restler" in selected_tools:
        commands["restler_ciktisi.txt"] = f"echo '[!] RESTler aracı OpenAPI (Swagger) JSON spesifikasyon dosyasına ihtiyaç duyar. Hedef URL: {target_url}'"

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        tool_name = output_filename.split('_')[0].upper()

        if stream_callback: stream_callback(f"[*] {tool_name} çalıştırılıyor...")
        logging.info(f"--> Çalıştırılıyor: {tool_name}...")
        
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_args, stream_callback=stream_callback)
        
        if stream_callback: stream_callback(f"[+] {tool_name} tamamlandı.")

    if stream_callback: stream_callback("\n[√] API Modülü işlemleri başarıyla tamamlandı.")
    return True