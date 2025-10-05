import os
import re
import google.generativeai as genai
import time
from tqdm import tqdm
import urllib.parse

def analyze_output_with_gemini(api_key, tool_name, file_content):
    """
    Verilen bir aracın çıktısını Gemini API kullanarak analiz eder ve risk seviyesi belirler.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Sen bir siber güvenlik uzmanısın ve bir sızma testi raporu hazırlıyorsun.
        Aşağıda '{tool_name}' adlı aracın ham çıktısı bulunmaktadır. Bu çıktıyı analiz ederek aşağıdaki formata uygun bir özet çıkar:

        **1. Aracın İşlevi:** Bu araç ne işe yarar? Kısaca açıkla.
        **2. Tespit Edilen Bulgular:** Çıktıda tespit edilen önemli güvenlik bulguları nelerdir? Varsa zafiyetleri, açık portları, bulunan dizinleri veya kritik bilgileri liste halinde belirt. Eğer önemli bir bulgu yoksa, "Bu taramada önemli bir güvenlik bulgusuna rastlanmamıştır." yaz.
        **3. Risk Seviyesi:** Tespit edilen bulguların genel risk seviyesini belirt (Kritik, Yüksek, Orta, Düşük, Bilgilendirici). Eğer bulgu yoksa "Bilgilendirici" olarak belirt.
        **4. Öneriler:** Tespit edilen bulgulara yönelik çözüm önerileri sun. Eğer bulgu yoksa, genel güvenlik sıkılaştırma önerilerinde bulun.
        **5. CVSS Puanı:** Tespit edilen bulgular için bir CVSS v3.1 skoru ve vektör string'i belirle (Örn: 7.5, CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N). Eğer bilgilendirici bir bulguysa veya zafiyet yoksa "N/A" yaz.
        **6. Zafiyet Detayı:** Eğer bir zafiyet tespit edildiyse, bu zafiyetin ne olduğunu (örn: SQL Injection, XSS, Missing Security Headers), nasıl sömürülebileceğini ve potansiyel etkilerini kısaca açıkla. Eğer bulgu yoksa bu başlığı tamamen atla.

        Lütfen cevabını sadece bu maddelere odaklanarak ve rapor formatında, Markdown kullanarak oluştur.

        --- HAM ÇIKTI ---
        {file_content}
        --- HAM ÇIKTI SONU ---
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[-] Gemini API ile analiz sırasında hata oluştu: {e}")
        return f"**Analiz Başarısız Oldu**\n\n**Risk Seviyesi:** Bilgilendirici\n\nHata Detayı: {str(e)}"

def create_executive_summary(api_key, all_analyses):
    """
    Tüm bireysel analizleri kullanarak bir yönetici özeti oluşturur.
    """
    print("[+] Yönetici özeti oluşturuluyor...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        prompt = f"""
        Sen bir lider sızma testi uzmanısın. Aşağıda, farklı güvenlik araçlarının analiz sonuçları bulunmaktadır. 
        Bu sonuçların tamamını gözden geçirerek, hedef sistemin genel güvenlik durumu hakkında üst yönetime sunulacak, 
        teknik olmayan bir dilde yazılmış 2-3 paragraflık bir **Yönetici Özeti** oluştur. 
        
        Özetinde şu noktalara değin:
        - Testin genel amacı.
        - En kritik bulgular (örneğin, eksik HTTP başlıkları, açık portlar, bilgi sızıntıları).
        - Sistemin genel güvenlik duruşu hakkındaki görüşün (zayıf, orta, iyi).
        - Atılması gereken en öncelikli adımlar.

        --- BİREYSEL ANALİZLER ---
        {all_analyses}
        --- BİREYSEL ANALİZLER SONU ---
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[-] Yönetici özeti oluşturulurken hata oluştu: {e}")
        return "Yönetici özeti oluşturulurken bir hata meydana geldi."

def parse_risk_level(text):
    """
    Analiz metninden risk seviyesini çıkaran yardımcı fonksiyon.
    """
    # DÜZELTME: Regex'i daha esnek hale getirerek olası boşlukları ve format farklılıklarını tolere ediyoruz.
    match = re.search(r"\*\*3\. Risk Seviyesi:\s*\*\*([a-zA-ZğüşıöçĞÜŞİÖÇ]+)", text)
    if match:
        return match.group(1).lower().replace('ü', 'u').replace('ş', 's').replace('ı', 'i').replace('ö', 'o').replace('ğ', 'g').replace('ç', 'c')
    return "bilgilendirici"

def generate_report(output_dir, domain, api_key):
    """
    Tüm .txt çıktılarını okur, Gemini ile analiz eder ve gelişmiş bir HTML raporu oluşturur.
    """
    print("\n[+] 5. Raporlama modülü başlatılıyor...")
    report_file_path = os.path.join(output_dir, "pentest_raporu_v2.html")
    
    output_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]
    analysis_results = {}
    raw_outputs = {}

    print("[+] Gemini AI ile çıktılar analiz ediliyor...")
    for filename in tqdm(output_files, desc="Analiz İlerlemesi"):
        tool_name = filename.replace('_ciktisi.txt', '').replace('_', ' ').title()
        file_path = os.path.join(output_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                raw_outputs[tool_name] = content
                if not content.strip():
                    analysis_results[tool_name] = "**Analiz Yapılamadı**\n\n**Risk Seviyesi:** Bilgilendirici\n\nÇıktı dosyası boş."
                    continue
            
            analysis = analyze_output_with_gemini(api_key, tool_name, content)
            analysis_results[tool_name] = analysis
        except Exception as e:
            analysis_results[tool_name] = f"**Hata**\n\n**Risk Seviyesi:** Bilgilendirici\n\nDosya okunurken bir sorun oluştu: {e}"

    risk_counts = {"kritik": 0, "yüksek": 0, "orta": 0, "düşük": 0, "bilgilendirici": 0}
    for analysis in analysis_results.values():
        level = parse_risk_level(analysis)
        if level in risk_counts:
            risk_counts[level] += 1

    full_analysis_text = "\n\n".join(f"--- {name} Analizi ---\n{text}" for name, text in analysis_results.items())
    executive_summary = create_executive_summary(api_key, full_analysis_text)

    chart_config = f"""
    {{
      type: 'pie',
      data: {{
        labels: ['Kritik', 'Yüksek', 'Orta', 'Düşük', 'Bilgilendirici'],
        datasets: [{{
          data: [{risk_counts['kritik']}, {risk_counts['yüksek']}, {risk_counts['orta']}, {risk_counts['düşük']}, {risk_counts['bilgilendirici']}],
          backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#007bff', '#28a745'],
        }}],
      }},
      options: {{
        title: {{
          display: true,
          text: 'Bulgu Risk Dağılımı',
          fontColor: '#343a40',
          fontSize: 18,
        }},
        legend: {{
          position: 'right',
          labels: {{
            fontColor: '#495057',
            fontSize: 14,
          }}
        }},
      }},
    }}
    """
    chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(chart_config)}"
    
    print("[+] Gelişmiş HTML raporu oluşturuluyor...")
    # ... (HTML içeriği aynı kaldığı için buraya eklenmedi) ...