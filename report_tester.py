# core/report_tester.py (GÜNCELLENMİŞ)

import os
# report_module'ü 'core' paketi içinden import et
from core import report_module
import sys

def main():
    """
    Sadece raporlama modülünü test etmek için kullanılır.
    Mevcut bir tarama çıktı klasörünü kullanarak raporu yeniden oluşturur.
    ANA DİZİNDEN (app.py'nin olduğu yerden) çalıştırılmalıdır:
    python core/report_tester.py
    """
    print("----------------------------------------------------")
    print("  HydraScan - Raporlama Modülü Test Aracı")
    print("----------------------------------------------------")
    print("[i] Bu scripti projenin ana dizininden (app.py'nin olduğu yerden)")
    print("[i] 'python core/report_tester.py' komutuyla çalıştırdığınızdan emin olun.")

    # Komut satırı argümanından klasör yolunu al (örn: scan_outputs/scan_5)
    if len(sys.argv) > 1:
        # Argümanı olduğu gibi al (relatif veya absolute olabilir)
        output_dir_relative = sys.argv[1] 
        print(f"[i] Komut satırından '{output_dir_relative}' klasörü seçildi.")
    else:
        # Kullanıcıdan mevcut bir rapor klasörünün GÖRECELİ yolunu al
        output_dir_relative = input("Lütfen analiz edilecek mevcut rapor klasörünün YOLUNU girin (örn: scan_outputs/scan_5): ")

    # Girilen yolun gerçekten var olup olmadığını kontrol et
    # os.path.abspath kullanarak tam yola çevirelim
    output_dir_absolute = os.path.abspath(output_dir_relative)

    if not os.path.isdir(output_dir_absolute):
        print(f"[-] Hata: '{output_dir_absolute}' adında bir klasör bulunamadı.")
        print(f"[i] Lütfen geçerli bir yol girin (örn: scan_outputs/scan_5).")
        return

    # Rapor başlığında kullanılacak domain adını kullanıcıdan alalım
    # Klasör adından çıkarmak yerine sormak daha garanti
    domain = input("Lütfen rapor başlığında kullanılacak domain adını girin (örn: www.mgorkemkilic.com): ")
    if not domain:
         domain = os.path.basename(output_dir_absolute) # Domain girilmezse klasör adını kullan

    api_key = input("Lütfen Google Gemini API anahtarınızı girin: ")
    if not api_key:
        print("[-] Hata: API anahtarı girilmedi.")
        return

    print(f"\n[+] '{output_dir_absolute}' klasörü kullanılarak rapor oluşturuluyor...")

    # Güncellenmiş report_module.generate_report fonksiyonunu çağır
    # Bu fonksiyon artık sadece output_dir, domain ve api_key alıyor.
    report_path = report_module.generate_report(output_dir_absolute, domain, api_key)

    if report_path:
        print(f"\n[+] Rapor başarıyla oluşturuldu/güncellendi: '{report_path}'")
    else:
         print(f"\n[-] Rapor oluşturma başarısız oldu. Logları kontrol edin.")


if __name__ == "__main__":
    main()