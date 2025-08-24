import subprocess
import os

def build_custom_image():
    """
    Tüm gerekli pentest araçlarını içeren özel bir Docker imajı oluşturur.
    """
    image_name = "pentest-araci-kali:v1.5" # Yeni araç eklediğimiz için sürümü artırıyoruz
    print(f"[+] '{image_name}' özel Docker imajı kontrol ediliyor/oluşturuluyor...")

    # DÜZELTME: dalfox kurulumu eklendi.
    dockerfile_content = """
FROM kalilinux/kali-rolling
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    whois \
    dnsutils \
    subfinder \
    nmap \
    nikto \
    gobuster \
    wordlists \
    sqlmap \
    commix \
    dirb \
    ffuf \
    xsser \
    ca-certificates \
    git \
    golang \
    python3-pip \
    responder \
    samba-client \
    awscli \
    apktool && \
    pip install apkleaks --break-system-packages && \
    go install github.com/assetnote/kiterunner/cmd/kiterunner@latest && \
    go install github.com/hahwul/dalfox/v2@latest && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/go/bin:${PATH}"
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)

    try:
        process = subprocess.run(
            ["docker", "build", "-t", image_name, "."], 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='ignore'
        )
    except subprocess.CalledProcessError as e:
        print(f"[-] Hata: Docker imajı oluşturulurken bir sorun oluştu.")
        error_detail = e.stderr if e.stderr else e.stdout
        print(f"[-] Hata Detayı: {error_detail}")
        return None
    finally:
        if os.path.exists("Dockerfile"):
            os.remove("Dockerfile")

    print(f"[+] '{image_name}' imajı hazır ve güncel.")
    return image_name

def run_command_in_docker(command, output_file_path, image_name, extra_docker_args=None):
    """
    Verilen bir komutu, belirtilen Docker imajı içinde çalıştırır ve çıktısını dosyaya yazar.
    """
    output_dir = os.path.dirname(output_file_path)
    
    base_docker_command = [
        "docker", "run", "--rm", "--network=host",
        "-v", f"{os.path.abspath(output_dir)}:/output"
    ]

    if extra_docker_args and isinstance(extra_docker_args, list):
        base_docker_command.extend(extra_docker_args)
    
    full_docker_command = base_docker_command + [
        image_name, "/bin/bash", "-c", command
    ]
    
    print(f"\n[+] Komut çalıştırılıyor: '{command.split()[0]}'")
    
    try:
        process = subprocess.run(
            full_docker_command, 
            check=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        full_output = process.stdout + "\n" + process.stderr
        with open(output_file_path, "w") as f:
            f.write(full_output)
            
        print(f"[+] Komut başarıyla tamamlandı. Çıktı '{os.path.basename(output_file_path)}' dosyasına kaydedildi.")
    except subprocess.CalledProcessError as e:
        error_message = f"--- HATA OLUŞTU ---\nKomut çalıştırılamadı: {full_docker_command}\nHata: {e}"
        # Hata durumunda stdout ve stderr'i birleştirip yaz
        full_error_output = e.stdout + "\n" + e.stderr
        with open(output_file_path, "w") as f:
            f.write(error_message + "\n" + full_error_output)
        print(f"[-] Komut çalıştırılırken bir hata oluştu: {e}")