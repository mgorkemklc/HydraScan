import os
from docker_helper import run_command_in_docker

def run_web_tests(domain, output_dir, image_name):
    """
    Yaygın web uygulaması zafiyetlerini tarayan araçları çalıştırır.
    """
    print("\n[+] 3. Web Uygulaması Güvenlik Testleri modülü başlatılıyor...")

    dir_wordlist = "/usr/share/wordlists/dirb/common.txt"

    commands = {
        # DÜZELTME: Gobuster'a wildcard yanıtları görmezden gelmesi için --wildcard eklendi.
        "gobuster_ciktisi.txt": f"gobuster dir -u http://{domain} -w {dir_wordlist} -t 50 --wildcard",
        
        "sqlmap_ciktisi.txt": f"sqlmap -u http://{domain} --crawl=1 --forms --batch --level=3 --risk=2",
        
        # DÜZELTME: xsser yerine daha modern ve etkili olan dalfox kullanılıyor.
        "dalfox_ciktisi.txt": f"dalfox url http://{domain} --silence",
        
        "commix_ciktisi.txt": f"commix -u http://{domain} --crawl=1 --batch",
        
        "dirb_ciktisi.txt": f"dirb http://{domain} {dir_wordlist}"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    print("\n[+] Web Uygulaması Güvenlik Testleri modülü tamamlandı.")