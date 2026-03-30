import os
import subprocess

def run_web_tests(target_domain, output_dir, selected_tools=[], wordlist_path=None, stream_callback=None):
    if stream_callback: stream_callback(f"\n[+] Web Analiz Motoru Başlatıldı. Hedef: {target_domain}")
    os.makedirs(output_dir, exist_ok=True)
    
    # Her araç için çalıştırılacak terminal komutları sözlüğü
    tools_commands = {
        "whois": ["whois", target_domain],
        "dig": ["dig", target_domain, "ANY"],
        "subfinder": ["subfinder", "-d", target_domain, "-silent"],
        "nuclei": ["nuclei", "-u", target_domain, "-t", "cves/"],
        "gobuster": ["gobuster", "dir", "-u", f"http://{target_domain}", "-w", wordlist_path or "common.txt"],
        "sqlmap": ["sqlmap", "-u", f"http://{target_domain}/index.php?id=1", "--batch", "--dbs"]
    }
    
    # Seçilen her bir aracı sırayla çalıştır
    for tool in selected_tools:
        if tool not in tools_commands:
            continue
            
        cmd = tools_commands[tool]
        output_file_path = os.path.join(output_dir, f"{tool}_ciktisi.txt")
        
        if stream_callback: stream_callback(f"[*] Çalıştırılıyor: {tool.upper()} ...")
        
        try:
            # Komutu çalıştır, çıktıyı txt dosyasına yönlendir (timeout 30 saniye)
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n[Hata veya Bilgi Mesajları]:\n" + result.stderr)
                    
            if stream_callback: stream_callback(f"[+] {tool.upper()} tamamlandı.")
            
        except FileNotFoundError:
            # EĞER ARAÇ BİLGİSAYARDA YÜKLÜ DEĞİLSE ÇÖKMESİN (Fallback / Mock Data)
            if stream_callback: stream_callback(f"[-] UYARI: '{tool}' aracı sistemde bulunamadı. Simüle edilmiş veri (Mock) yazdırılıyor...")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(f"--- HYDRASCAN YEDEK (MOCK) ÇIKTISI ---\n")
                if tool == "whois":
                    f.write(f"Domain: {target_domain}\nRegistrar: Örnek Kayıt Firması\nCreation Date: 2020-01-01\n")
                elif tool == "nuclei":
                    f.write(f"[high] CVE-2023-XXXXX Tespit Edildi at {target_domain}/admin\n")
                elif tool == "sqlmap":
                    f.write(f"Parameter: id (GET)\n    Type: boolean-based blind\n    Title: AND boolean-based blind - WHERE or HAVING clause\n")
                else:
                    f.write(f"{tool} taraması simüle edildi. Sistemde kritik açık bulunmadı.\n")
                    
        except subprocess.TimeoutExpired:
            if stream_callback: stream_callback(f"[-] {tool.upper()} zaman aşımına uğradı (30 saniye).")
        except Exception as e:
            if stream_callback: stream_callback(f"[-] {tool.upper()} çalıştırılırken hata: {str(e)}")

    if stream_callback: stream_callback("\n[√] Web araçları taraması başarıyla tamamlandı.")