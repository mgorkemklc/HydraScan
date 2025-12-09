# core/report_module.py

import os
import json
import google.generativeai as genai
import logging
from tqdm import tqdm

def analyze_output_with_gemini(api_key, tool_name, file_content):
    """
    Çıktıyı analiz eder ve JSON formatında (Python dict string) döndürür.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash') # Hızlı model
        
        # PROMPT'U DEĞİŞTİRİYORUZ: HTML yerine JSON istiyoruz.
        prompt = f"""
        Sen bir siber güvenlik uzmanısın. Aşağıda '{tool_name}' aracının çıktısı var.
        Bu çıktıyı analiz et ve yanıtını SADECE aşağıdaki JSON formatında ver. 
        Markdown veya başka bir metin ekleme. Sadece saf JSON döndür.

        {{
            "arac_adi": "{tool_name}",
            "ozet": "Aracın ne bulduğuna dair 1-2 cümlelik kısa özet",
            "risk_seviyesi": "Kritik | Yüksek | Orta | Düşük | Bilgilendirici",
            "bulgular": [
                "Bulgu 1",
                "Bulgu 2"
            ],
            "oneriler": [
                "Öneri 1",
                "Öneri 2"
            ]
        }}

        --- HAM ÇIKTI ---
        {file_content}
        --- HAM ÇIKTI SONU ---
        """

        response = model.generate_content(prompt)
        
        # Gemini bazen JSON'ı ```json ... ``` blokları içine alır, onları temizleyelim
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return clean_text

    except Exception as e:
        logging.error(f"[-] Gemini API hatası ({tool_name}): {e}")
        # Hata durumunda boş bir JSON yapısı döndür
        return json.dumps({
            "arac_adi": tool_name,
            "ozet": f"Analiz sırasında hata oluştu: {str(e)}",
            "risk_seviyesi": "Hata",
            "bulgular": [],
            "oneriler": []
        })

def generate_report(output_dir, domain, api_key):
    """
    Tüm çıktıları analiz eder ve tek bir JSON dosyasında birleştirir.
    """
    logging.info("\n[+] Raporlama modülü başlatılıyor (JSON Modu)...")
    
    full_report_data = {
        "domain": domain,
        "analizler": []
    }

    if not os.path.isdir(output_dir):
        return None

    output_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]

    for filename in tqdm(output_files, desc="Analiz İlerlemesi"):
        tool_name = filename.replace('_ciktisi.txt', '').replace('_', ' ').title()
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                continue
            
            # Gemini'den JSON string al
            json_response_str = analyze_output_with_gemini(api_key, tool_name, content)
            
            # String'i Python Dictionary'e çevir
            try:
                analysis_dict = json.loads(json_response_str)
                full_report_data["analizler"].append(analysis_dict)
            except json.JSONDecodeError:
                # Eğer Gemini bozuk JSON dönerse manuel ekle
                full_report_data["analizler"].append({
                    "arac_adi": tool_name,
                    "ozet": "AI çıktısı ayrıştırılamadı (JSON Hatası).",
                    "risk_seviyesi": "Bilinmiyor",
                    "bulgular": [json_response_str[:200] + "..."], # Ham metnin başını koy
                    "oneriler": []
                })
                
        except Exception as e:
            logging.error(f"[-] Dosya işlenirken hata: {e}")

    # Raporu JSON dosyası olarak kaydet
    report_filename = "pentest_raporu.json"
    report_path = os.path.join(output_dir, report_filename)

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report_data, f, ensure_ascii=False, indent=4)
        
        logging.info(f"[+] JSON Rapor kaydedildi: {report_path}")
        return report_path
        
    except Exception as e:
        logging.error(f"[-] Rapor yazma hatası: {e}")
        return None