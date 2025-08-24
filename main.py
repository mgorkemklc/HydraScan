import os
import time
import docker_helper
import recon_module
import web_app_module
import api_module
import internal_network_module
import cloud_module
import mobile_module
import report_module
import concurrent.futures

def create_output_directory(domain):
    """
    Komut çıktılarının saklanacağı, zaman damgalı benzersiz bir dizin oluşturur.
    Windows'ta geçersiz olan karakterleri temizler.
    """
    # DÜZELTME: Windows'ta geçersiz olan ':' gibi karakterleri '_' ile değiştiriyoruz.
    sanitized_domain = domain.replace('.', '_').replace(':', '_')
    
    output_dir = f"pentest_raporu_{sanitized_domain}_{time.strftime('%Y%m%d-%H%M%S')}"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"[+] Çıktılar için '{output_dir}' dizini oluşturuldu.")
        print(f"[+] Çıktıların tam yolu: {os.path.abspath(output_dir)}")
    return output_dir

def get_clean_domain(domain_with_port):
    """
    'localhost:3000' gibi bir girdiden portu temizleyerek 'localhost' döndürür.
    """
    if ':' in domain_with_port:
        return domain_with_port.split(':')[0]
    return domain_with_port

def main():
    """
    Uygulamanın ana akışını yönetir.
    """
    print("----------------------------------------------------")
    print("  Sentinel AI Güvenlik Platformu v2.0 - Paralel")
    print("----------------------------------------------------")
    domain_input = input("Lütfen test edilecek alan adını (örn: site.com veya localhost:3000) girin: ")
    internal_ip_range = input("İç ağ taraması için IP aralığı girin (örn: 192.168.1.0/24) [atlamak için Enter'a basın]: ")
    run_cloud_scan = input("Bulut (AWS) taraması yapmak ister misiniz? (e/h): ").lower()
    aws_keys = {}
    if run_cloud_scan == 'e':
        aws_keys['access_key'] = input("  Lütfen AWS Access Key ID girin: ")
        aws_keys['secret_key'] = input("  Lütfen AWS Secret Access Key girin: ")
        aws_keys['region'] = input("  Lütfen AWS Region girin (örn: us-east-1): ")
    apk_file_path = input("Mobil (.apk) analizi için dosya yolunu girin [atlamak için Enter'a basın]: ")
    api_key = input("Lütfen Google Gemini API anahtarınızı girin: ")
    if not api_key:
        print("[-] Gemini API anahtarı girilmedi. Raporlama adımı atlanacak.")
        return
    output_dir = create_output_directory(domain_input)
    
    # DÜZELTME: Portu temizlenmiş domain'i diğer modüllere gönderiyoruz.
    clean_domain = get_clean_domain(domain_input)

    # --- Docker Ortamını Hazırlama ---
    print("\n[+] Docker ortamı hazırlanıyor...")
    image_name = docker_helper.build_custom_image()
    if not image_name:
        print("[-] Docker imajı oluşturulamadığı için işlem durduruldu.")
        return

    # --- Test Modüllerini Çalıştırma ---
    try:
        print("\n[+] Bağımsız test modülleri paralel olarak başlatılıyor...")
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(recon_module.run_reconnaissance, clean_domain, domain_input, output_dir, image_name),
                executor.submit(web_app_module.run_web_tests, domain_input, output_dir, image_name),
                executor.submit(api_module.run_api_tests, domain_input, output_dir, image_name)
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"[-] Paralel bir görevde hata oluştu: {e}")
        print("\n[+] Paralel görevler tamamlandı.")
        
        if internal_ip_range:
            internal_network_module.run_internal_tests(internal_ip_range, output_dir, image_name)
        else:
            print("\n[i] İç ağ tarama adımı atlandı.")
        if aws_keys:
            cloud_module.run_cloud_tests(
                aws_keys['access_key'], aws_keys['secret_key'], aws_keys['region'],
                output_dir, image_name
            )
        else:
            print("\n[i] Bulut ortamı tarama adımı atlandı.")
        if apk_file_path:
            mobile_module.run_mobile_tests(apk_file_path, output_dir, image_name)
        else:
            print("\n[i] Mobil uygulama analizi adımı atlandı.")

    except Exception as e:
        print(f"[-] Testler sırasında beklenmedik bir hata oluştu: {e}")
        return

    # --- Raporlama ---
    report_module.generate_report(output_dir, domain_input, api_key)
    
    print(f"\n[+] Tüm işlemler başarıyla tamamlandı. Raporunuz '{output_dir}' dizininde bulunmaktadır.")


if __name__ == "__main__":
    main()