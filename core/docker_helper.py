import subprocess
import os
import logging

def run_command_in_docker(command, output_file_path, image_name="pentest-araci-kali:v1.5", extra_docker_args=None):
    """
    Verilen komutu Docker içinde çalıştırır ve çıktıyı yerel dosyaya yazar.
    DNS sorunlarını çözmek için 8.8.8.8 eklenmiştir.
    """
    
    # 1. Çıktı klasörünü hazırla
    output_dir = os.path.dirname(output_file_path)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            logging.error(f"[-] Klasör oluşturulamadı: {e}")
            return

    # 2. Docker Komutunu Oluştur
    # --network=host: Ana makine ağını kullan (Hız ve erişim için)
    # --dns=8.8.8.8: Google DNS kullan (Dig/Whois timeout çözümü)
    base_docker_command = [
        "docker", "run", "--rm", 
        "--network=host",
        "--dns=8.8.8.8", 
        "-v", f"{os.path.abspath(output_dir)}:/app/output" # Volume mount (Opsiyonel ama güvenli)
    ]

    if extra_docker_args and isinstance(extra_docker_args, list):
        base_docker_command.extend(extra_docker_args)
    
    full_docker_command = base_docker_command + [
        image_name, "/bin/bash", "-c", command
    ]
    
    logging.info(f"[+] Docker komutu: {' '.join(full_docker_command)}")
    
    full_output = ""
    
    try:
        # 3. Komutu Çalıştır
        process = subprocess.run(
            full_docker_command, 
            check=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace' # Türkçe karakter hatasını önle
        )
        full_output = process.stdout + "\n" + process.stderr
        
    except subprocess.CalledProcessError as e:
        error_msg = f"--- HATA OLUŞTU ---\nKomut: {command}\nHata Kodu: {e.returncode}\nÇıktı:\n{e.stdout}\nHata Çıktısı:\n{e.stderr}"
        full_output = error_msg
        logging.error(f"[-] Komut hatası: {e}")
    
    except FileNotFoundError:
        full_output = "--- KRİTİK: DOCKER BULUNAMADI ---\nLütfen Docker Desktop uygulamasının açık olduğundan emin olun."
        logging.error("[-] Docker bulunamadı.")

    except Exception as e:
        full_output = f"--- BEKLENMEYEN HATA ---\n{str(e)}"
        logging.error(f"[-] Beklenmeyen hata: {e}")

    # 4. Çıktıyı Dosyaya Yaz
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(full_output)
        logging.info(f"[+] Çıktı kaydedildi: {output_file_path}")
    except Exception as e:
        logging.error(f"[-] Dosya yazma hatası ({output_file_path}): {e}")

def build_docker_image_stream(dockerfile="Dockerfile.pentest", tag="pentest-araci-kali:v1.5"):
    """
    Docker imajını yeniden inşa eder ve logları canlı (stream) olarak döner.
    DNS ve Ağ ayarları eklenmiştir.
    """
    cmd = ["docker", "build", "--network=host", "-t", tag, "-f", dockerfile, "."]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace'
    )

    for line in process.stdout:
        yield line

    process.wait()
    
    if process.returncode != 0:
        raise Exception(f"Docker build başarısız. Hata kodu: {process.returncode}")