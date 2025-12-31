import subprocess
import os
import logging
import time

# Loglama yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command_in_docker(command, output_file_path, image_name="pentest-araci-kali:v1.5", extra_docker_args=None, stream_callback=None):
    """
    Verilen komutu Docker içinde çalıştırır.
    - stream_callback: Canlı terminal çıktısı için fonksiyon (GUI'ye veri basar).
    - timeout: 900 saniye (15dk) manuel kontrol edilir.
    """
    
    # Çıktı klasörünü oluştur
    output_dir = os.path.dirname(output_file_path)
    if not os.path.exists(output_dir):
        try: os.makedirs(output_dir)
        except: pass

    # Temel Docker argümanları
    # --network=host: Amass vb. araçların ağ hatası vermemesi için kritik.
    cmd_args = [
        "docker", "run", "--rm",
        "--network=host", 
        "--dns=8.8.8.8",
        "-v", f"{os.path.abspath(output_dir)}:/app/output"
    ]

    if extra_docker_args:
        cmd_args.extend(extra_docker_args)
    
    # Komutu oluştur
    full_cmd = cmd_args + [image_name, "/bin/bash", "-c", command]
    
    log_msg = f"[+] Docker Komutu: {' '.join(full_cmd)}\n"
    logging.info(log_msg.strip())
    
    # Eğer GUI callback varsa logu oraya da gönder
    if stream_callback: stream_callback(log_msg)

    full_output = []
    start_time = time.time()
    
    try:
        # Popen ile canlı okuma başlatıyoruz (Senin kodundaki yapı)
        process = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Satır satır okuma döngüsü
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            
            if line:
                full_output.append(line)
                if stream_callback: stream_callback(line) # GUI'ye anlık gönder
            
            # Manuel Timeout Kontrolü (15 Dakika)
            if time.time() - start_time > 900:
                process.kill()
                timeout_msg = "\n[!] ZAMAN AŞIMI: İşlem 15 dakikayı geçtiği için sonlandırıldı.\n"
                full_output.append(timeout_msg)
                if stream_callback: stream_callback(timeout_msg)
                break
        
        if process.returncode is not None and process.returncode != 0:
             err = f"\n[!] İşlem hata koduyla bitti: {process.returncode}\n"
             if stream_callback: stream_callback(err)

    except Exception as e:
        err_msg = f"\n[-] Kritik Hata: {str(e)}\n"
        full_output.append(err_msg)
        if stream_callback: stream_callback(err_msg)

    # Sonuçları dosyaya kaydet
    final_text = "".join(full_output)
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(final_text)
    except Exception as e:
        logging.error(f"Dosya yazma hatası: {e}")

def build_docker_image_stream(dockerfile="Dockerfile.pentest", tag="pentest-araci-kali:v1.5"):
    """
    Docker imajını build ederken çıktıyı stream eder.
    """
    cmd = ["docker", "build", "--network=host", "-t", tag, "-f", dockerfile, "."]
    
    # Build işlemini başlat ve çıktıyı yield et
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