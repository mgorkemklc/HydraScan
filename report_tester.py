import os
import report_module

def main():
    """
    Sadece raporlama modülünü test etmek için kullanılır.
    Mevcut bir tarama çıktı klasörünü kullanarak raporu yeniden oluşturur.
    """
    print("----------------------------------------------------")
    print("  HydraScan - Raporlama Modülü Test Aracı")
    print("----------------------------------------------------")
    
    # Kullanıcıdan mevcut bir rapor klasörünün yolunu al
    # Örnek: pentest_raporu_www_mgorkemkilic_com_20251009-182309
    output_dir = input("Lütfen analiz edilecek mevcut rapor klasörünün adını girin: ")

    if not os.path.isdir(output_dir):
        print(f"[-] Hata: '{output_dir}' adında bir klasör bulunamadı.")
        print("[i] Lütfen main.py ile daha önce oluşturulmuş geçerli bir klasör adı girin.")
        return

    # Rapor başlığında kullanılacak domain adını klasör adından çıkar
    try:
        # 'pentest_raporu_' ve sondaki zaman damgasını kaldırarak domain'i al
        domain_part = output_dir.replace('pentest_raporu_', '')
        domain = '_'.join(domain_part.split('_')[:-1]).replace('_', '.')
    except Exception:
        domain = "Bilinmeyen Hedef" # Eğer klasör adı beklenenden farklıysa

    api_key = input("Lütfen Google Gemini API anahtarınızı girin: ")
    if not api_key:
        print("[-] Hata: API anahtarı girilmedi.")
        return

    print(f"\n[+] '{output_dir}' klasörü kullanılarak rapor oluşturuluyor...")
    
    # Sadece raporlama modülünü çağır
    report_module.generate_report(output_dir, domain, api_key)
    
    print(f"\n[+] Rapor başarıyla oluşturuldu/güncellendi. '{os.path.join(output_dir, 'pentest_raporu_v2.html')}' dosyasını kontrol edebilirsiniz.")


if __name__ == "__main__":
    main()
