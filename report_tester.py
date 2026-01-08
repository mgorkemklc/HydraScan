import os
import sys
# .env dosyasını okumak için gerekli (yoksa pip install python-dotenv yapmalısın)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Kütüphane yoksa sadece input ile devam eder

# Core modüllerini bulabilmesi için path ayarı
sys.path.append(os.getcwd())

from core import report_module

def manual_test():
    print("-" * 50)
    print("   MANUEL RAPORLAMA VE PDF TEST ARACI")
    print("-" * 50)

    # 1. API KEY GÜVENLİĞİ
    # Önce .env dosyasından veya sistemden okumaya çalış
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Eğer bulunamazsa kullanıcıdan iste
    if not api_key:
        print("[!] API Anahtarı çevresel değişkenlerde bulunamadı.")
        api_key = input("[?] Lütfen Gemini API Key giriniz: ").strip()
    
    if not api_key:
        print("[-] HATA: API Anahtarı girilmedi. İşlem iptal ediliyor.")
        return

    # 2. Kullanıcıdan Scan ID iste
    scan_id = input("[?] İşlem yapılacak Scan ID (örn: 16): ").strip()
    if not scan_id:
        print("[-] Scan ID girilmedi.")
        return

    target_domain = input("[?] Hedef Domain (örn: mgorkemkilic.com): ").strip() or "test-target.com"
    
    # 3. Klasör yolunu belirle
    base_dir = os.getcwd()
    scan_folder = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")
    
    print(f"\n[*] Hedef Klasör: {scan_folder}")
    
    if not os.path.exists(scan_folder):
        print(f"[-] HATA: '{scan_folder}' klasörü bulunamadı!")
        return

    # 4. Dosyaları Kontrol Et
    files = [f for f in os.listdir(scan_folder) if f.endswith(".txt")]
    if not files:
        print("[-] HATA: Klasörde hiç .txt çıktı dosyası yok.")
        return
    print(f"[+] Klasörde {len(files)} adet araç çıktısı bulundu.")

    # 5. JSON RAPOR OLUŞTURMA (Gemini)
    print("\n[1/2] Yapay Zeka Analizi Başlatılıyor...")
    
    # API key parametre olarak gönderiliyor
    json_path = report_module.generate_report(scan_folder, target_domain, api_key)
    
    if json_path and os.path.exists(json_path):
        print(f"[+] JSON Rapor Oluşturuldu: {json_path}")
    else:
        print("[-] JSON oluşturma başarısız oldu. API Key veya kotanızı kontrol edin.")
        return

    # 6. PDF ÇEVİRME
    print("\n[2/2] PDF'e Dönüştürülüyor...")
    pdf_output_path = os.path.join(scan_folder, f"Manual_Report_{scan_id}.pdf")
    
    final_pdf = report_module.export_to_pdf(json_path, pdf_output_path)
    
    if final_pdf and os.path.exists(final_pdf):
        print(f"\n[OK] İŞLEM BAŞARILI! PDF Konumu:")
        print(f"     {final_pdf}")
        
        # Windows'ta otomatik aç
        try:
            os.startfile(final_pdf)
        except:
            pass
    else:
        print("[-] PDF oluşturulamadı.")

if __name__ == "__main__":
    manual_test()