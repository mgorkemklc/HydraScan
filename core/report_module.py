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
# Alternatif indirme linki
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"

def check_and_download_font():
    if not os.path.exists(FONTS_DIR):
        try: os.makedirs(FONTS_DIR)
        except OSError: pass
    
    # Dosya yoksa veya boyutu çok küçükse indir
    if not os.path.exists(FONT_PATH) or os.path.getsize(FONT_PATH) < 50000:
        print(f"[*] Font indiriliyor...")
        try:
            r = requests.get(FONT_URL, timeout=20)
            if r.status_code == 200:
                with open(FONT_PATH, 'wb') as f: f.write(r.content)
                return True
        except: pass
        return False
    return True

def read_tool_outputs(scan_folder):
    combined_output = ""
    files = glob.glob(os.path.join(scan_folder, "*_*.txt"))
    if not files: return "Araç çıktısı bulunamadı."

    for file_path in files:
        tool_name = os.path.basename(file_path).split('_')[0].upper()
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
                if content:
                    combined_output += f"\n=== {tool_name} ===\n{content[:8000]}\n"
        except: pass
    return combined_output

def generate_report(scan_folder_path, target_domain, api_key):
    if not api_key or not os.path.exists(scan_folder_path): return None
    
    tool_outputs = read_tool_outputs(scan_folder_path)
    
    prompt = f"""
    Sen Pentest Uzmanısın. Hedef: '{target_domain}'.
    
    GÖREV: Araç çıktılarını analiz et, Türkçe JSON rapor oluştur.
    
    ÇIKTI FORMATI (SADECE JSON):
    {{
        "domain": "{target_domain}",
        "analizler": [
            {{
                "arac_adi": "Araç Adı",
                "risk_seviyesi": "KRITIK|YÜKSEK|ORTA|DÜŞÜK|BILGI",
                "ozet": "Teknik özet",
                "bulgular": ["Bulgu 1"],
                "oneriler": ["Öneri 1"]
            }}
        ]
    }}
    
    VERİLER:
    {tool_outputs}
    """

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(prompt)
        
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        report_json = json.loads(raw_text)
        
        # JSON'u diske kaydet ki PDF fonksiyonu bulabilsin
        json_path = os.path.join(scan_folder_path, "pentest_raporu.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_json, f, ensure_ascii=False, indent=4)
            
        return json_path
    except Exception as e:
        print(f"Rapor Hatası: {e}")
        return None

class PDFReport(FPDF):
    def __init__(self, target_domain):
        super().__init__()
        self.target_domain = target_domain
        self.set_auto_page_break(auto=True, margin=15)
        
        # Font varsa yükle, yoksa Helvetica (Türkçe karakterleri bozar ama çalışır)
        self.use_unicode = False
        if check_and_download_font():
            try:
                self.add_font(FONT_NAME, "", FONT_PATH, uni=True)
                self.main_font = FONT_NAME
                self.use_unicode = True
            except: self.main_font = "Helvetica"
        else:
            self.main_font = "Helvetica"

    def safe_text(self, text):
        # Eğer Unicode font yoksa Türkçe karakterleri çevir
        if self.use_unicode: return str(text)
        replacements = {"ı":"i", "İ":"I", "ğ":"g", "Ğ":"G", "ü":"u", "Ü":"U", "ş":"s", "Ş":"S", "ö":"o", "Ö":"O", "ç":"c", "Ç":"C"}
        text = str(text)
        for k,v in replacements.items(): text = text.replace(k,v)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def header(self):
        self.set_font(self.main_font, "", 10)
        self.set_text_color(100)
        self.cell(0, 10, self.safe_text(f"HydraScan - {self.target_domain}"), ln=True, align="R")
        self.ln(5)

    def chapter_title(self, label, risk):
        colors = {"KRITIK": (220,53,69), "YÜKSEK": (253,126,20), "ORTA": (255,193,7)}
        r,g,b = (100,100,100)
        for k, v in colors.items():
            if k in risk.upper(): r,g,b = v; break
        
        self.set_font(self.main_font, "", 14)
        self.set_fill_color(r,g,b); self.set_text_color(255)
        self.cell(0, 10, self.safe_text(f" {label} ({risk}) "), ln=True, fill=True)
        self.ln(4)
        self.set_text_color(0)

    def chapter_body(self, text):
        self.set_font(self.main_font, "", 11)
        # Genişliği elle ayarla (190mm sayfa genişliği - marginler)
        self.multi_cell(180, 6, self.safe_text(text))
        self.ln()

def export_to_pdf(json_path, output_path=None):
    if not os.path.exists(json_path): return None
    try:
        with open(json_path, 'r', encoding='utf-8') as f: data = json.load(f)
        
        pdf = PDFReport(data.get("domain", "Hedef"))
        pdf.add_page()
        
        pdf.set_font(pdf.main_font, "", 24)
        pdf.cell(0, 20, pdf.safe_text("Sızma Testi Raporu"), ln=True, align="C"); pdf.ln(10)
        
        for a in data.get("analizler", []):
            pdf.chapter_title(a.get("arac_adi", ""), a.get("risk_seviyesi", ""))
            pdf.chapter_body(a.get("ozet", ""))
            if a.get("bulgular"):
                pdf.set_font(pdf.main_font, "", 10)
                for b in a["bulgular"]:
                    pdf.cell(5)
                    pdf.multi_cell(175, 5, self.safe_text(f"- {b}")) # Genişlik ayarı
                pdf.ln(5)
                
        if not output_path: output_path = json_path.replace(".json", ".pdf")
        pdf.output(output_path)
        return output_path
    except Exception as e:
        print(f"PDF Hatası: {e}")
        return None