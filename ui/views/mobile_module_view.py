import customtkinter as ctk
from tkinter import filedialog
import os
import threading
import datetime
from ui.theme import COLORS

# Çekirdek modülleri içe aktarıyoruz
from core.mobile_module import run_mobile_tests
from core.report_module import generate_report

class MobileModuleView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Mobil Uygulama Güvenlik Taraması", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # 1. Dosya Yükleme Alanı
        upload_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        upload_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(upload_frame, text="1. APK veya AAB Dosyasını Yükle", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(20, 5))
        
        file_input_frame = ctk.CTkFrame(upload_frame, fg_color="transparent")
        file_input_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.lbl_apk_path = ctk.CTkLabel(file_input_frame, text="Henüz dosya seçilmedi...", text_color=COLORS["text_gray"], font=("Roboto", 12, "italic"))
        self.lbl_apk_path.pack(side="left", padx=10)

        ctk.CTkButton(file_input_frame, text="📁 Dosya Seç", width=120, fg_color=COLORS["bg_input"], hover_color=COLORS["border"], text_color="white", command=self.select_apk).pack(side="right")
        self.selected_apk_path = None

        # 2. Gelişmiş Mobil Tarama Seçenekleri
        options_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        options_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(options_frame, text="2. Analiz Modülleri", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(20, 15))

        self.mob_tools_vars = {
            "mobsf_sast": ctk.BooleanVar(value=True),
            "secrets_scanner": ctk.BooleanVar(value=True),
            "malware_check": ctk.BooleanVar(value=False),
            "frida_dast": ctk.BooleanVar(value=False)
        }

        labels = {
            "mobsf_sast": "MobSF Statik Analiz (Temel Raporlama)",
            "secrets_scanner": "Hassas Veri Taraması (Decompile edip gizli API Key / AWS Token arar)",
            "malware_check": "Zararlı Yazılım Analizi (Quark Engine ile zararlı davranış tespiti)",
            "frida_dast": "Frida Dinamik Analiz (Kök erişimi ve SSL Pinning kontrolü)"
        }

        for key, var in self.mob_tools_vars.items():
            cb = ctk.CTkCheckBox(options_frame, text=labels[key], variable=var, text_color="white", fg_color=COLORS["accent"], border_color=COLORS["border"])
            cb.pack(anchor="w", padx=30, pady=8)

        # 3. Canlı Terminal ve Takip Barı (YENİ EKLENEN KISIM)
        self.progress_bar = ctk.CTkProgressBar(scroll, progress_color=COLORS["accent"])
        self.progress_bar.pack(fill="x", pady=(20, 5))
        self.progress_bar.set(0) # Başlangıçta boş
        
        term_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        term_frame.pack(fill="x", pady=(5, 10))
        
        ctk.CTkLabel(term_frame, text=">_ CANLI İŞLEM LOGLARI", font=("Consolas", 12, "bold"), text_color=COLORS["success"]).pack(anchor="w", padx=10, pady=(10, 0))
        self.terminal_box = ctk.CTkTextbox(term_frame, height=150, fg_color=COLORS["log_bg"], text_color=COLORS["terminal_fg"], font=("Consolas", 11))
        self.terminal_box.pack(fill="x", padx=10, pady=10)
        self.terminal_box.insert("0.0", "[*] Sistem hazır. Dosya seçip taramayı başlatın...\n")

        # Başlat Butonu
        self.btn_mob_launch = ctk.CTkButton(scroll, text="MOBİL TARAMAYI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=self.launch_scan)
        self.btn_mob_launch.pack(fill="x", pady=20)

    def select_apk(self):
        path = filedialog.askopenfilename(filetypes=[("Android Package", "*.apk *.aab *.xapk")])
        if path:
            self.selected_apk_path = path
            self.lbl_apk_path.configure(text=os.path.basename(path), text_color="white")

    def launch_scan(self):
        # Dosya seçilmemişse uyar
        if not self.selected_apk_path:
            self.terminal_box.insert("end", "[-] HATA: Lütfen analiz edilecek bir uygulama dosyası seçin!\n")
            self.terminal_box.see("end")
            return

        # Arayüzü tarama moduna geçir
        self.btn_mob_launch.configure(state="disabled", text="TARAMA VE ANALİZ DEVAM EDİYOR ⏳", fg_color=COLORS["warning"], text_color="black")
        self.progress_bar.set(0.1)
        self.terminal_box.insert("end", f"\n=====================================\n[*] YENİ GÖREV: {os.path.basename(self.selected_apk_path)}\n")
        
        selected_tools = [tool for tool, var in self.mob_tools_vars.items() if var.get()]
        
        # Tarama çıktıları için klasör oluştur (Örn: scan_outputs/mob_20260330_123456)
        scan_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.getcwd(), "scan_outputs", f"mob_{scan_id}")
        
        # Arayüzün (GUI) donmaması için işlemi ayrı bir Thread'de başlatıyoruz!
        threading.Thread(target=self._run_scan_thread, args=(self.selected_apk_path, output_dir, selected_tools), daemon=True).start()

    def _run_scan_thread(self, apk_path, output_dir, selected_tools):
        # Arka plandan terminale yazı yazdırmamızı sağlayan köprü fonksiyon
        def stream_callback(msg):
            self.terminal_box.insert("end", msg + "\n")
            self.terminal_box.see("end")

        try:
            self.progress_bar.set(0.3)
            # 1. Aşama: Kodları Parçala ve Şifreleri Bul
            run_mobile_tests(apk_path, output_dir, selected_tools, stream_callback)
            self.progress_bar.set(0.7)
            
            # 2. Aşama: Gemini-3-Flash ile ISO 27001 Raporu Oluştur
            stream_callback("\n[*] AI Analizi (Gemini-3-Flash) başlatılıyor...")
            api_key = self.app.config.get("api_key", "")
            
            if not api_key:
                stream_callback("[-] UYARI: Gemini API Key eksik. Rapor oluşturulamadı! Ayarlar'dan key ekleyin.")
            else:
                report_path = generate_report(output_dir, os.path.basename(apk_path), api_key)
                if report_path:
                    stream_callback(f"[+] Kusursuz! ISO 27001 Raporu oluşturuldu: {os.path.basename(report_path)}")
            
            self.progress_bar.set(1.0)
            stream_callback("\n[+] GÖREV BAŞARIYLA TAMAMLANDI!")

        except Exception as e:
            stream_callback(f"\n[-] KRİTİK HATA: İşlem sırasında bir sorun oluştu: {str(e)}")
            self.progress_bar.set(0)
        finally:
            # İşlem bitince butonu eski haline getir
            self.btn_mob_launch.configure(state="normal", text="MOBİL TARAMAYI BAŞLAT 🚀", fg_color=COLORS["success"], text_color="white")