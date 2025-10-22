import os
from docker_helper import run_command_in_docker

def run_api_tests(domain, output_dir, image_name):
    """
    API endpoint'lerini keşfetmek için araçlar çalıştırır.
    """
    print("\n[+] 4. API Güvenlik Testleri modülü başlatılıyor...")
    api_wordlist = "/usr/share/wordlists/dirb/common.txt"
    target_url = f"https://{domain}"

    commands = {
        "ffuf_api_ciktisi.txt": f"ffuf -w {api_wordlist} -u {target_url}/FUZZ -t 100",
        "ffuf_api_v1_ciktisi.txt": f"ffuf -w {api_wordlist} -u {target_url}/api/v1/FUZZ -t 100",
        "ffuf_api_v2_ciktisi.txt": f"ffuf -w {api_wordlist} -u {target_url}/api/v2/FUZZ -t 100"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name)

    print("\n[+] API Güvenlik Testleri modülü tamamlandı.")