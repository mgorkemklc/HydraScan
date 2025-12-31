import os
import json
import time
import google.generativeai as genai
import logging

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def analyze_output_with_gemini(api_key, tool_name, file_content):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""
        Sen kıdemli bir siber güvenlik uzmanısın. Aşağıda '{tool_name}' aracının çıktısı var.
        Bu çıktıyı analiz et ve yanıtını SADECE aşağıdaki JSON formatında ver.
        
        ÖNEMLİ KURAL: 
        Eğer çıktı içinde "command not found", "error", "stdin", "failed", "no such file" gibi ifadeler varsa veya araç hiç çalışmamışsa,
        "risk_seviyesi" alanını mutlaka "ARAÇ HATASI" olarak doldur ve özette sorunu belirt.
        
        JSON Formatı:
        {{
            "arac_adi": "{tool_name}",
            "ozet": "Aracın durumu ve ne bulduğuna dair 1-2 cümlelik özet. Hata varsa burada belirt.",
            "risk_seviyesi": "Kritik | Yüksek | Orta | Düşük | Bilgilendirici | ARAÇ HATASI",
            "bulgular": [ "Bulgu 1", "Bulgu 2" ],
            "oneriler": [ "Öneri 1", "Öneri 2" ]
        }}

        --- HAM ÇIKTI ---
        {file_content[:15000]}  # Çok uzun çıktıları kırp
        --- HAM ÇIKTI SONU ---
        """

        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return clean_text

    except Exception as e:
        logging.error(f"[-] Gemini API hatası ({tool_name}): {e}")
        return json.dumps({
            "arac_adi": tool_name,
            "ozet": f"Analiz sırasında hata oluştu: {str(e)[:100]}...",
            "risk_seviyesi": "ARAÇ HATASI",
            "bulgular": ["AI servisine erişilemedi."],
            "oneriler": ["API anahtarını kontrol edin."]
        })

def generate_report(output_dir, domain, api_key):
    full_report_data = { "domain": domain, "analizler": [] }
    if not os.path.isdir(output_dir): return None

    output_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]

    for filename in output_files: # tqdm kaldırdık, app.py zaten progress bar yönetiyor
        tool_name = filename.replace('_ciktisi.txt', '').replace('_', ' ').title()
        file_path = os.path.join(output_dir, filename)
        
        try:
            time.sleep(5) # Hızlandırmak için süreyi kısalttım (20 -> 5)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip(): continue
            
            json_response_str = analyze_output_with_gemini(api_key, tool_name, content)
            try:
                analysis_dict = json.loads(json_response_str)
                full_report_data["analizler"].append(analysis_dict)
            except: pass
                
        except Exception as e:
            logging.error(f"[-] Hata: {e}")

    report_path = os.path.join(output_dir, "pentest_raporu.json")
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report_data, f, ensure_ascii=False, indent=4)
        return report_path
    except: return None
    
def export_to_pdf(json_report_path, output_pdf_path):
    if not os.path.exists(json_report_path): return False
    try:
        with open(json_report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doc = SimpleDocTemplate(output_pdf_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph(f"HydraScan Raporu: {data.get('domain')}", styles['Title']))
        elements.append(Spacer(1, 20))

        for analiz in data.get("analizler", []):
            risk = analiz.get('risk_seviyesi', 'Bilinmiyor')
            elements.append(Paragraph(f"{analiz.get('arac_adi')} - Risk: {risk}", styles['Heading2']))
            elements.append(Paragraph(f"<b>Özet:</b> {analiz.get('ozet')}", styles['Normal']))
            
            if analiz.get("bulgular"):
                data_table = [["Bulgular"]] + [[b] for b in analiz.get("bulgular")]
                t = Table(data_table, colWidths=[400])
                t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black), ('BACKGROUND', (0,0), (-1,0), colors.lightgrey)]))
                elements.append(t)
            
            elements.append(Spacer(1, 15))

        doc.build(elements)
        return True
    except Exception as e:
        print(f"PDF Hatası: {e}")
        return False

def ai_analyze_false_positive(finding_text, api_key):
    """Bulgunun False Positive olup olmadığını Gemini'ye sorar."""
    if not api_key: return "Hata: API Key bulunamadı."
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Aşağıdaki siber güvenlik taraması bulgusunu analiz et.
        Bunun bir 'False Positive' (Hatalı Alarm) olma ihtimali nedir?
        
        Bulgu: {finding_text}
        
        Lütfen cevabı şu formatta ver:
        - Karar: [Yüksek İhtimalle False Positive / Gerçek Zafiyet / Belirsiz]
        - Güven Skoru: %0-100
        - Teknik Açıklama: (Kısa açıklama)
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Servis Hatası: {str(e)}"