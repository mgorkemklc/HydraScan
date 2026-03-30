import os
import glob
import json
from fpdf import FPDF

# YENİ NESİL GEMINI SDK'SI
from google import genai

def generate_report(output_dir, target_domain, api_key):
    print(f"[*] AI Raporlama Motoru Başlatıldı: {target_domain}")
    
    # 1. Tüm Tarama Çıktılarını Oku
    all_logs_content = ""
    txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
    
    if not txt_files:
        print("[-] Analiz edilecek tarama logu (TXT dosyası) bulunamadı.")
        return None

    for file_path in txt_files:
        tool_name = os.path.basename(file_path).replace("_ciktisi.txt", "").upper()
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                all_logs_content += f"\n--- {tool_name} ARACI ÇIKTISI ---\n{content[:10000]}\n"
        except Exception as e:
            pass

    # 2. Gemini İçin Mükemmel Prompt (Sistem Talimatı)
    prompt = f"""
    Sen kıdemli bir Siber Güvenlik Uzmanı ve Sızma Testi (Pentest) analistisin.
    Aşağıda {target_domain} hedefine yapılan güvenlik taramalarının ham log çıktıları bulunmaktadır.
    Bu logları analiz et ve Birebir aşağıdaki JSON formatında bir rapor oluştur. JSON DIŞINDA HİÇBİR METİN YAZMA.

    İstenen Çıktı Formatı:
    {{
      "domain": "{target_domain}",
      "genel_skor": 0 ile 100 arası bir güvenlik puanı,
      "analizler": [
        {{
          "arac_adi": "Zafiyeti bulan aracın adı",
          "risk_seviyesi": "Kritik, Yüksek, Orta veya Düşük",
          "ozet": "Zafiyetin tam olarak ne olduğu (Türkçe)",
          "iso27001_kontrol": "Bu zafiyet ISO 27001'in hangi maddesini ihlal ediyor?",
          "bulgular": ["Bulgu 1", "Bulgu 2"],
          "oneriler": ["Çözüm 1", "Çözüm 2"]
        }}
      ]
    }}

    TARAMA LOGLARI:
    {all_logs_content}
    """

    # 3. Yeni SDK ile Gemini'ye İsteği Gönder
    try:
        print("[*] Gemini yapay zekası logları analiz ediyor (Bu işlem 30-60 saniye sürebilir)...")
        
        # Yeni Client yapısı
        client = genai.Client(api_key=api_key)
        
        # API'de 404 almamak için şimdilik en stabil yeni nesil modeli kullanıyoruz
        response = client.models.generate_content(
            model='gemini-3.1-pro', 
            contents=prompt,
        )
        
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        report_data = json.loads(response_text)
        
        report_path = os.path.join(output_dir, "pentest_raporu.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=4)
            
        print(f"[+] AI Raporu başarıyla oluşturuldu: {report_path}")
        return report_path

    except json.JSONDecodeError:
        print("[-] Gemini geçerli bir JSON formatı döndürmedi.")
        return None
    except Exception as e:
        print(f"[-] Gemini API Hatası: {e}")
        return None

# export_to_pdf fonksiyonu aynen kalabilir...
def export_to_pdf(json_path, save_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(200, 10, txt="HYDRASCAN - SIZMA TESTI VE ISO 27001 UYUMLULUK RAPORU", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(200, 10, txt=f"Hedef: {data.get('domain', 'Bilinmiyor')}", ln=True)
        pdf.cell(200, 10, txt=f"Genel Guvenlik Skoru: {data.get('genel_skor', '?')} / 100", ln=True)
        pdf.ln(10)

        for analiz in data.get("analizler", []):
            pdf.set_font("Helvetica", 'B', 12)
            baslik = f"[{analiz.get('risk_seviyesi', 'INFO').upper()}] {analiz.get('arac_adi', 'Arac')}"
            baslik = baslik.replace('Ş', 'S').replace('ı', 'i').replace('ğ', 'g').replace('Ü', 'U').replace('Ç', 'C').replace('Ö', 'O')
            pdf.cell(200, 10, txt=baslik, ln=True)
            
            pdf.set_font("Helvetica", 'I', 10)
            iso = f"ISO 27001 Ihlali: {analiz.get('iso27001_kontrol', 'Belirtilmemis')}"
            iso = iso.replace('Ş', 'S').replace('ı', 'i').replace('ğ', 'g').replace('Ü', 'U').replace('Ç', 'C').replace('Ö', 'O')
            pdf.cell(200, 8, txt=iso, ln=True)
            
            pdf.set_font("Helvetica", '', 10)
            ozet = analiz.get("ozet", "").replace('ş','s').replace('ı','i').replace('ğ','g').replace('ü','u').replace('ç','c').replace('ö','o')
            pdf.multi_cell(0, 8, txt=f"Ozet: {ozet}")
            pdf.ln(5)

        pdf.output(save_path)
        return True
    except Exception:
        return False