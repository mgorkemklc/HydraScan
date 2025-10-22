import subprocess
import os
import logging
import tempfile # Geçici dosya oluşturmak için

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

def run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name, extra_docker_args=None):
    """
    Verilen komutu Docker içinde çalıştırır.
    Çıktıyı alır, bir geçici dosyaya yazar, S3'e yükler ve geçici dosyayı siler.
    s3_key: S3'e hangi isimle kaydedileceği (örn: media/scan_outputs/1/nmap_ciktisi.txt)
    """
    
    # Çıktıyı yazmak için güvenli bir geçici dosya oluştur
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_output:
        temp_file_path = temp_output.name
        output_dir = os.path.dirname(temp_file_path) # Geçici dosyanın dizini
    
    base_docker_command = [
        "docker", "run", "--rm", "--network=host",
        # Geçici dosyanın olduğu dizini Docker'a bağlıyoruz
        "-v", f"{os.path.abspath(output_dir)}:/output"
    ]

    if extra_docker_args and isinstance(extra_docker_args, list):
        base_docker_command.extend(extra_docker_args)
    
    full_docker_command = base_docker_command + [
        image_name, "/bin/bash", "-c", command
    ]
    
    logging.info(f"\n[+] Komut çalıştırılıyor: '{command.split()[0]}'")
    full_output = ""
    
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
        
    except subprocess.CalledProcessError as e:
        error_message = f"--- HATA OLUŞTU ---\nKomut çalıştırılamadı: {full_docker_command}\nHata: {e}"
        full_output = error_message + "\n" + e.stdout + "\n" + e.stderr
        logging.error(f"[-] Komut çalıştırılırken bir hata oluştu: {e}")
    
    finally:
        # 1. Çıktıyı geçici dosyaya yaz
        try:
            with open(temp_file_path, "w", encoding='utf-8', errors='ignore') as f:
                f.write(full_output)
            
            # 2. Geçici dosyayı S3'e yükle
            s3_client.upload_file(temp_file_path, bucket_name, s3_key)
            logging.info(f"[+] Çıktı S3'e yüklendi: {s3_key}")
            
        except Exception as s3_e:
            logging.error(f"[-] S3 yükleme hatası ({s3_key}): {s3_e}")
            
        # 3. Geçici dosyayı her durumda sil
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)