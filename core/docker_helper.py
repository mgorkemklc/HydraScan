# core/docker_helper.py (YENİ - YEREL DİSKE YAZAN HALİ)

import subprocess
import os
import logging

def run_command_in_docker(command, output_file_path, image_name, extra_docker_args=None):
    """
    Verilen komutu Docker içinde çalıştırır.
    Çıktıyı (stdout/stderr) alır ve doğrudan yerel bir dosyaya yazar.
    
    output_file_path: Çıktının kaydedileceği tam dosya yolu 
                      (örn: C:\\...\\scan_outputs\\scan_1\\nmap_ciktisi.txt)
    """
    
    # DİKKAT: Bu fonksiyonun çalışması için bu Python kodunu çalıştıran
    # makinede Docker'ın kurulu ve çalışıyor olması gerekir.
    
    base_docker_command = [
        "docker", "run", "--rm", "--network=host",
    ]
    
    # Docker komutuna mount edilmesi gereken yerel klasörler varsa ekle
    # (örn: /output klasörünü bağlamak)
    output_dir = os.path.dirname(output_file_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # ÖNEMLİ: Docker'ın çıktı yazabilmesi için yerel klasörü mount etmeliyiz.
    # Container içindeki /output yolunu, yerel makinedeki output_dir'e bağlıyoruz.
    base_docker_command.extend(["-v", f"{os.path.abspath(output_dir)}:/output"])

    if extra_docker_args and isinstance(extra_docker_args, list):
        base_docker_command.extend(extra_docker_args)
    
    full_docker_command = base_docker_command + [
        image_name, "/bin/bash", "-c", command
    ]
    
    logging.info(f"\n[+] Komut çalıştırılıyor: '{command.split()[0]}'")
    full_output = ""
    
    try:
        # Komutu çalıştır
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
        error_message = f"--- KRİTİK HATA: DOCKER BULUNAMADI ---\n{e}\n" \
                        "Bu komutu çalıştıran makinede Docker'ın kurulu ve çalışır olduğundan emin olun."
        full_output = error_message
        logging.error(error_message)

    finally:
        # Çıktıyı S3 yerine YEREL DOSYAYA yaz
        try:
            # DİKKAT: Eğer komut (örn: apktool) çıktısını dosyaya kendi yazıyorsa
            # bu bloğa gerek kalmayabilir, ancak nmap, whois gibi stdout
            # üreten araçlar için bu blok şarttır.
            
            # Eğer komut çıktısını /output/dosya_adi olarak kendi yazıyorsa
            # bu bloğu atlayabiliriz, ancak biz genelde stdout'u yakalıyoruz.
            # Güvenli olması için biz yine de yakalanan stdout'u dosyaya yazalım.
            
            # Eğer komut /output/dosya_adi'na yazıyorsa (örn: airodump),
            # bu komutun stdout'u boş olabilir, bu durumda bu dosya da boş olur.
            # Bu yüzden komutları /output/dosya_adi'na yönlendirmek daha iyi.
            
            # -------- YENİ YAKLAŞIM (Daha Basit) --------
            # `docker_helper` çıktıyı dosyaya yazmasın.
            # Komutun kendisi çıktıyı > /output/dosya_adi.txt olarak yazsın.
            # Bu `docker_helper` sadece komutu çalıştırsın ve hata loglasın.
            
            # Geri alıyorum, eski yöntem (stdout'u yakalayıp dosyaya yazmak) 
            # daha stabil, ona dönelim.
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(full_output)
            
            logging.info(f"[+] Çıktı yerel diske yazıldı: {output_file_path}")
            
        except Exception as e:
            logging.error(f"[-] Yerel çıktı dosyası yazılırken hata ({output_file_path}): {e}")