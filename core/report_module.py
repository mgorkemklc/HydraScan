import os
import json
import time  # <-- ÖNEMLİ
import google.generativeai as genai
import logging
from tqdm import tqdm

def analyze_output_with_gemini(api_key, tool_name, file_content):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""
        Sen bir siber güvenlik uzmanısın. Aşağıda '{tool_name}' aracının çıktısı var.
        Bu çıktıyı analiz et ve yanıtını SADECE aşağıdaki JSON formatında ver. 
        Markdown veya başka bir metin ekleme. Sadece saf JSON döndür.

        {{
            "arac_adi": "{tool_name}",
            "ozet": "Aracın ne bulduğuna dair 1-2 cümlelik kısa özet",
            "risk_seviyesi": "Kritik | Yüksek | Orta | Düşük | Bilgilendirici",
            "bulgular": [ "Bulgu 1", "Bulgu 2" ],
            "oneriler": [ "Öneri 1", "Öneri 2" ]
        }}

        --- HAM ÇIKTI ---
        {file_content}
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
            "risk_seviyesi": "Hata",
            "bulgular": [],
            "oneriler": []
        })

def generate_report(output_dir, domain, api_key):
    logging.info("\n[+] Raporlama modülü başlatılıyor (JSON Modu)...")
    full_report_data = { "domain": domain, "analizler": [] }

    if not os.path.isdir(output_dir): return None

    output_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]

    for filename in tqdm(output_files, desc="Analiz İlerlemesi"):
        tool_name = filename.replace('_ciktisi.txt', '').replace('_', ' ').title()
        file_path = os.path.join(output_dir, filename)
        
        try:
            # --- API KOTASI İÇİN BEKLEME ---
            logging.info(f"[*] {tool_name} analiz ediliyor... (Kota için 5sn bekleniyor)")
            time.sleep(5) 
            # -------------------------------

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip(): continue
            
            json_response_str = analyze_output_with_gemini(api_key, tool_name, content)
            
            try:
                analysis_dict = json.loads(json_response_str)
                full_report_data["analizler"].append(analysis_dict)
            except json.JSONDecodeError:
                full_report_data["analizler"].append({
                    "arac_adi": tool_name,
                    "ozet": "AI çıktısı ayrıştırılamadı (JSON Hatası).",
                    "risk_seviyesi": "Bilinmiyor",
                    "bulgular": [],
                    "oneriler": []
                })
                
        except Exception as e:
            logging.error(f"[-] Dosya işlenirken hata: {e}")

    report_filename = "pentest_raporu.json"
    report_path = os.path.join(output_dir, report_filename)

    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report_data, f, ensure_ascii=False, indent=4)
        return report_path
    except Exception as e:
        logging.error(f"[-] Rapor yazma hatası: {e}")
        return None