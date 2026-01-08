import os
import json
import glob
import time
import requests
import google.generativeai as genai
from fpdf import FPDF

# --- AYARLAR ---
FONTS_DIR = os.path.join(os.getcwd(), "assets", "fonts")
FONT_NAME = "DejaVuSans"
FONT_PATH = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"

# --- YARDIMCI: FONT İNDİRME ---
def check_and_download_font():
    """Türkçe karakter destekleyen fontu kontrol eder, yoksa indirir."""
    if not os.path.exists(FONTS_DIR):
        try:
            os.makedirs(FONTS_DIR)
        except OSError:
            pass 
    
    if not os.path.exists(FONT_PATH):
        try:
            r = requests.get(FONT_URL, timeout=10)
            with open(FONT_PATH, 'wb') as f:
                f.write(r.content)
        except Exception as e:
            print(f"[-] Font indirme hatası: {e}")
            return False
    return True

# =============================================================================
# BÖLÜM 1: GEMINI AI İLE RAPOR OLUŞTURMA (ANALİZ)
# =============================================================================

def read_tool_outputs(scan_folder):
    """Tarama klasöründeki tüm .txt çıktılarını okur ve birleştirir."""
    combined_output = ""
    files = glob.glob(os.path.join(scan_folder, "*_*.txt"))
    
    if not files:
        return "Herhangi bir araç çıktısı bulunamadı."

    for file_path in files:
        tool_name = os.path.basename(file_path).split('_')[0].upper()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if content:
                    combined_output += f"\n\n=== {tool_name} ÇIKTISI ===\n{content}\n"
                    combined_output += "="*30
        except Exception as e:
            print(f"Dosya okuma hatası ({file_path}): {e}")
            
    return combined_output

def generate_report(scan_folder_path, target_domain, api_key):
    """
    DÜZELTME: app.py ile uyumlu olması için fonksiyon adı 'generate_report' yapıldı.
    """
    if not api_key:
        print("[-] API Anahtarı eksik!")
        return None

    if not os.path.exists(scan_folder_path):
        print(f"[-] Klasör bulunamadı: {scan_folder_path}")
        return None

    tool_outputs = read_tool_outputs(scan_folder_path)

    # --- PROMPT TASARIMI ---
    prompt = f"""
    Sen kıdemli bir Siber Güvenlik ve Sızma Testi Uzmanısın (Pentester).
    Aşağıda, '{target_domain}' hedefi için yapılan otomatik tarama araçlarının ham çıktıları bulunmaktadır.
    
    GÖREVİN:
    Bu çıktıları analiz ederek profesyonel, teknik ve yönetici özetini içeren bir sızma testi raporu oluşturmak.
    
    ÇIKTI FORMATI (KESİNLİKLE JSON OLMALI):
    Cevabın SADECE geçerli bir JSON objesi olmalı. Markdown, ```json``` etiketi veya ek metin kullanma.
    
    JSON ŞEMASI:
    {{
        "domain": "{target_domain}",
        "analizler": [
            {{
                "arac_adi": "Araç İsmi (Örn: Nmap)",
                "risk_seviyesi": "KRITIK | YÜKSEK | ORTA | DÜŞÜK | BILGI | ARAÇ HATASI",
                "ozet": "Bulguların kısa ve anlaşılır teknik özeti.",
                "bulgular": [
                    "Teknik bulgu 1",
                    "Teknik bulgu 2"
                ],
                "oneriler": [
                    "Çözüm önerisi 1",
                    "Çözüm önerisi 2"
                ]
            }}
        ]
    }}

    KURALLAR:
    1. Eğer bir araç hata verdiyse (Örn: 'Failed to resolve', 'Connection refused'), risk_seviyesi'ni 'ARAÇ HATASI' veya 'BILGI' yap ve hatayı özetle.
    2. Dil Türkçe olmalı.
    3. Bulgular teknik ve net olmalı.
    
    --- ARAÇ ÇIKTILARI ---
    {tool_outputs}
    """

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        print(f"[*] Gemini analizi başlıyor...")
        response = model.generate_content(prompt)
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        
        report_json = json.loads(raw_text.strip())
        
        json_path = os.path.join(scan_folder_path, "pentest_raporu.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, ensure_ascii=False, indent=4)
            
        print(f"[+] JSON Rapor oluşturuldu: {json_path}")
        return json_path

    except Exception as e:
        print(f"[-] AI Raporlama Hatası: {e}")
        return None

# =============================================================================
# BÖLÜM 2: PDF ÇIKTISI
# =============================================================================

class PDFReport(FPDF):
    def __init__(self, target_domain):
        super().__init__()
        self.target_domain = target_domain
        self.set_auto_page_break(auto=True, margin=15)
        
        if check_and_download_font():
            self.add_font(FONT_NAME, "", FONT_PATH, uni=True)
            self.main_font = FONT_NAME
        else:
            self.main_font = "Arial"

    def header(self):
        self.set_font(self.main_font, "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"HydraScan - {self.target_domain}", ln=True, align="R")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.main_font, "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Sayfa {self.page_no()}", align="C")

    def chapter_title(self, arac_adi, risk_level):
        colors = {
            "KRITIK": (220, 53, 69), "YÜKSEK": (253, 126, 20),
            "ORTA": (255, 193, 7), "DÜŞÜK": (40, 167, 69),
            "BILGI": (23, 162, 184), "ARAÇ HATASI": (108, 117, 125)
        }
        
        risk_key = risk_level.upper().replace("İ", "I").replace("ı", "I")
        r, g, b = (108, 117, 125)
        
        for k, v in colors.items():
            if k in risk_key:
                r, g, b = v
                break

        self.set_font(self.main_font, "", 14)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        
        title_text = f" {arac_adi} - Risk: {risk_level} "
        self.cell(0, 10, title_text, ln=True, fill=True)
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, text):
        self.set_font(self.main_font, "", 11)
        self.multi_cell(0, 6, text)
        self.ln()

    def add_list_item(self, text):
        self.set_font(self.main_font, "", 11)
        self.cell(5)
        self.cell(5, 6, "-", align="R")
        self.multi_cell(0, 6, text)
        self.ln(1)

def export_to_pdf(json_path, output_path=None):
    """
    DÜZELTME: output_path parametresi eklendi.
    Böylece 'Farklı Kaydet' penceresinden gelen yol kullanılabilir.
    """
    if not os.path.exists(json_path):
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        target = data.get("domain", "Bilinmeyen Hedef")
        analizler = data.get("analizler", [])
        
        pdf = PDFReport(target)
        pdf.add_page()
        
        # Kapak
        pdf.ln(60)
        pdf.set_font(pdf.main_font, "", 24)
        pdf.cell(0, 10, "Sızma Testi Raporu", ln=True, align="C")
        pdf.set_font(pdf.main_font, "", 16)
        pdf.ln(10)
        pdf.cell(0, 10, target, ln=True, align="C")
        pdf.ln(20)
        pdf.set_font(pdf.main_font, "", 12)
        pdf.cell(0, 10, f"Tarih: {time.strftime('%d.%m.%Y')}", ln=True, align="C")
        pdf.add_page()

        # İçerik
        for analiz in analizler:
            arac = analiz.get("arac_adi", "Bilinmeyen")
            risk = analiz.get("risk_seviyesi", "Bilgi")
            ozet = analiz.get("ozet", "")
            
            pdf.chapter_title(arac, risk)
            
            pdf.set_font(pdf.main_font, "", 12)
            pdf.cell(0, 8, "Özet:", ln=True)
            pdf.chapter_body(ozet)
            
            if analiz.get("bulgular"):
                pdf.set_font(pdf.main_font, "", 12)
                pdf.cell(0, 8, "Teknik Bulgular:", ln=True)
                for b in analiz["bulgular"]:
                    pdf.add_list_item(str(b))
                pdf.ln(2)

            if analiz.get("oneriler"):
                pdf.set_font(pdf.main_font, "", 12)
                pdf.cell(0, 8, "Öneriler:", ln=True)
                for o in analiz["oneriler"]:
                    pdf.add_list_item(str(o))
            
            pdf.ln(5)

        if not output_path:
            output_path = json_path.replace(".json", ".pdf")
            
        pdf.output(output_path)
        return output_path

    except Exception as e:
        print(f"[-] PDF Oluşturma Hatası: {e}")
        return None