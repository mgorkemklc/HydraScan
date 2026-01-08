import os
# Artık 'core' bir alt klasör olduğu için importu bu şekilde yapıyoruz
from core import report_module
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    """
    Sadece raporlama modülünü test etmek için kullanılır.
    Mevcut bir tarama çıktı klasörünü kullanarak raporu yeniden oluşturur.
    ANA DİZİNDEN (app.py'nin olduğu yerden) çalıştırılmalıdır:
    python core/report_tester.py <yol/klasor_adi>
    """
    print("----------------------------------------------------")
    print("  HydraScan - Raporlama Modülü Test Aracı")
    print("----------------------------------------------------")
    print("[i] Bu scripti projenin ana dizininden (app.py'nin olduğu yerden)")
    print("[i] 'python core/report_tester.py scan_outputs/scan_X' komutuyla çalıştırın.")

    # Komut satırı argümanından klasör yolunu al (örn: scan_outputs/scan_5)
    if len(sys.argv) > 1:
        # Argümanı olduğu gibi al (relatif veya absolute olabilir)
        output_dir_input = sys.argv[1] 
        print(f"[i] Komut satırından '{output_dir_input}' klasör yolu alındı.")
    else:
        # Kullanıcıdan mevcut bir rapor klasörünün GÖRECELİ veya TAM yolunu al
        output_dir_input = input("Lütfen analiz edilecek mevcut rapor klasörünün YOLUNU girin (örn: scan_outputs/scan_5 veya C:\\...\\scan_5): ")

    # Girilen yolun gerçekten var olup olmadığını kontrol et
    # os.path.abspath, göreceli yolu tam yola çevirir, tam yolu olduğu gibi bırakır.
    output_dir_absolute = os.path.abspath(output_dir_input)

    if not os.path.isdir(output_dir_absolute):
        print(f"[-] Hata: Klasör bulunamadı: '{output_dir_absolute}'")
        print(f"[i] Lütfen geçerli bir klasör yolu girin.")
        return

    # Rapor başlığında kullanılacak domain adını kullanıcıdan alalım
    domain = input(f"Lütfen rapor başlığında kullanılacak domain adını girin (örn: {os.path.basename(output_dir_absolute).replace('scan_','')}): ")
    if not domain:
         domain = os.path.basename(output_dir_absolute).replace('scan_','') # Domain girilmezse klasör adından tahmin et

    api_key = input("Lütfen Google Gemini API anahtarınızı girin: ")
    if not api_key:
        print("[-] Hata: API anahtarı girilmedi.")
        return

    print(f"\n[+] '{output_dir_absolute}' klasörü kullanılarak rapor oluşturuluyor...")

    # Güncellenmiş report_module.generate_report fonksiyonunu çağır
    report_path = report_module.generate_report(output_dir_absolute, domain, api_key)

    if report_path:
        print(f"\n[+] Rapor başarıyla oluşturuldu/güncellendi: '{report_path}'")
    else:
         print(f"\n[-] Rapor oluşturma başarısız oldu. Hata mesajlarına bakın.")
