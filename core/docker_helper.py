# core/docker_helper.py (YENİ İÇERİK)

import subprocess
import os
import logging
# 'tempfile' importu kaldırıldı

def run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name, extra_docker_args=None):
    """
    Verilen komutu Docker içinde çalıştırır.
    Çıktıyı (stdout/stderr) alır ve doğrudan S3'e bir metin nesnesi olarak yükler.
    
    s3_key: S3'e hangi isimle kaydedileceği (örn: media/scan_outputs/1/nmap_ciktisi.txt)
    """
    
    # DİKKAT: Bu fonksiyonun çalışması için, bu kodu çalıştıran konteynerin
    # (yani Celery Worker'ın) Docker soketine erişimi olmalıdır.
    # Bu, ECS Task Definition'da bir volume mount ile yapılır:
    # /var/run/docker.sock:/var/run/docker.sock
    
    base_docker_command = [
        "docker", "run", "--rm", "--network=host",
        # Volume mount (-v) komutu ECS'de çalışmayacağı için kaldırıldı
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
    
    except FileNotFoundError as e:
        # Bu hata genellikle Celery Worker konteynerinde Docker'ın kurulu olmadığını
        # veya Docker soketine erişemediğini gösterir.
        error_message = f"--- KRİTİK HATA: DOCKER BULUNAMADI ---\n{e}\n" \
                        "Bu komutu çalıştıran (Celery) konteynerin Docker'a erişimi olduğundan emin olun."
        full_output = error_message
        logging.error(error_message)

    finally:
        # Çıktıyı geçici dosya yerine doğrudan S3'e 'put_object' ile yükle
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=full_output.encode('utf-8') # Metni byte'a çevir
            )
            logging.info(f"[+] Çıktı S3'e yüklendi: {s3_key}")
            
        except Exception as s3_e:
            logging.error(f"[-] S3 yükleme hatası ({s3_key}): {s3_e}")

# build_custom_image fonksiyonu kaldırıldı. İmajlar artık ECR'da.