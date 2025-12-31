import json
import os
import requests
from fpdf import FPDF

# --- AYARLAR ---
FONTS_DIR = os.path.join(os.getcwd(), "assets", "fonts")
FONT_NAME = "DejaVuSans"
FONT_PATH = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"

def check_and_download_font():
    """Türkçe karakter destekleyen fontu kontrol eder, yoksa indirir."""
    if not os.path.exists(FONTS_DIR):
        os.makedirs(FONTS_DIR)
    
    if not os.path.exists(FONT_PATH):
        print(f"[*] Font bulunamadı, indiriliyor: {FONT_NAME}...")
        try:
            r = requests.get(FONT_URL)
            with open(FONT_PATH, 'wb') as f:
                f.write(r.content)
            print(f"[+] Font başarıyla indirildi: {FONT_PATH}")
        except Exception as e:
            print(f"[-] Font indirme hatası: {e}")
            return False
    return True

class PDFReport(FPDF):
    def __init__(self, target_domain):
        super().__init__()
        self.target_domain = target_domain
        self.set_auto_page_break(auto=True, margin=15)
        
        # Türkçe Fontu Yükle
        if check_and_download_font():
            self.add_font(FONT_NAME, "", FONT_PATH, uni=True)
            self.main_font = FONT_NAME
        else:
            self.main_font = "Arial" # Yedek (Türkçe karakterler bozuk çıkabilir)

    def header(self):
        # Üst Bilgi
        self.set_font(self.main_font, "", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"HydraScan Güvenlik Raporu - {self.target_domain}", ln=True, align="R")
        self.ln(5)

    def footer(self):
        # Alt Bilgi (Sayfa Numarası)
        self.set_y(-15)
        self.set_font(self.main_font, "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Sayfa {self.page_no()}", align="C")

    def chapter_title(self, title, risk_level="Bilgi"):
        # Risk Seviyesine Göre Renk Belirle
        colors = {
            "KRITIK": (220, 53, 69),   # Kırmızı
            "CRITICAL": (220, 53, 69),
            "YÜKSEK": (253, 126, 20),  # Turuncu
            "HIGH": (253, 126, 20),
            "ORTA": (255, 193, 7),     # Sarı
            "MEDIUM": (255, 193, 7),
            "DÜŞÜK": (40, 167, 69),    # Yeşil
            "LOW": (40, 167, 69),
            "BILGI": (23, 162, 184),   # Mavi
            "INFO": (23, 162, 184),
            "HATA": (108, 117, 125)    # Gri
        }
        
        # Varsayılan renk (Gri)
        r, g, b = colors.get(risk_level.upper(), (108, 117, 125))
        
        self.set_font(self.main_font, "", 14)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255) # Beyaz yazı
        
        # Başlık Kutusu
        title_text = f" {title} "
        self.cell(0, 10, title_text, ln=True, fill=True)
        
        # Altındaki boşluk ve renk sıfırlama
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def chapter_body(self, body_text):
        self.set_font(self.main_font, "", 11)
        self.multi_cell(0, 6, body_text)
        self.ln()

    def add_list_item(self, item_text):
        self.set_font(self.main_font, "", 11)
        # Bullet point simgesi (Unicode)
        self.cell(5) # Girinti
        self.cell(5, 6, chr(149), align="R") # Nokta
        self.multi_cell(0, 6, item_text)
        self.ln(1)

def export_to_pdf(json_path):
    """
    JSON raporunu okur ve profesyonel PDF formatına dönüştürür.
    """
    if not os.path.exists(json_path):
        return None

    try:
        # 1. JSON Verisini Oku
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        target = data.get("domain", "Bilinmeyen Hedef")
        analizler = data.get("analizler", [])
        
        # 2. PDF Oluştur
        pdf = PDFReport(target)
        pdf.add_page()
        
        # --- KAPAK SAYFASI ---
        pdf.set_font(pdf.main_font, "", 24)
        pdf.ln(60)
        pdf.cell(0, 10, "Sızma Testi Raporu", ln=True, align="C")
        pdf.set_font(pdf.main_font, "", 16)
        pdf.ln(10)
        pdf.cell(0, 10, target, ln=True, align="C")
        pdf.ln(20)
        pdf.set_font(pdf.main_font, "", 12)
        pdf.cell(0, 10, "Oluşturulma Tarihi: " + os.path.basename(json_path).split('_')[0], ln=True, align="C") # Basit tarih
        pdf.add_page()

        # --- İÇERİK ---
        for analiz in analizler:
            arac_adi = analiz.get("arac_adi", "Bilinmeyen Araç")
            risk = analiz.get("risk_seviyesi", "Bilgi")
            ozet = analiz.get("ozet", "Özet bilgisi bulunamadı.")
            
            # Başlık (Renkli Kutu)
            pdf.chapter_title(f"{arac_adi} - Risk: {risk}", risk)
            
            # Özet Metni
            pdf.set_font(pdf.main_font, "", 12) # Biraz kalın/belirgin
            pdf.cell(0, 8, "Özet:", ln=True)
            pdf.chapter_body(ozet)
            
            # Bulgular Listesi
            bulgular = analiz.get("bulgular", [])
            if bulgular:
                pdf.set_font(pdf.main_font, "", 12)
                pdf.cell(0, 8, "Teknik Bulgular:", ln=True)
                for bulgu in bulgular:
                    # Uzun metinleri temizle
                    clean_bulgu = str(bulgu).replace("\n", " ").strip()
                    pdf.add_list_item(clean_bulgu)
                pdf.ln(2)

            # Öneriler Listesi
            oneriler = analiz.get("oneriler", [])
            if oneriler:
                pdf.set_font(pdf.main_font, "", 12)
                pdf.cell(0, 8, "Çözüm Önerileri:", ln=True)
                for oneri in oneriler:
                    pdf.add_list_item(str(oneri))
            
            pdf.ln(5) # Araçlar arası boşluk
            
            # Sayfa sonuna geldiysek yeni sayfaya geç (Otomatik yapılıyor ama bazen manuel gerekebilir)
            if pdf.get_y() > 250:
                pdf.add_page()

        # 3. Dosyayı Kaydet
        output_path = json_path.replace(".json", ".pdf")
        pdf.output(output_path)
        print(f"[+] PDF Raporu oluşturuldu: {output_path}")
        return output_path

    except Exception as e:
        print(f"[-] PDF Oluşturma Hatası: {e}")
        return None