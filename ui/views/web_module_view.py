import customtkinter as ctk
from tkinter import filedialog
import os
import threading
import datetime
from ui.theme import COLORS

# Çekirdek modülleri bağlıyoruz
from core.web_app_module import run_web_tests
from core.report_module import generate_report

class WebModuleView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(scroll, text="Web Uygulama Taraması", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        # 1. Hedef Bilgileri
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text="Web Hedefi (Domain veya URL)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.entry_web_domain = ctk.CTkEntry(info_frame, placeholder_text="örn: example.com", height=45, fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color="white")
        self.entry_web_domain.pack(fill="x", padx=20, pady=(0, 20))
        
        wl_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        wl_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(wl_frame, text="Özel Wordlist (Gobuster):", text_color="gray").pack(side="left")
        self.lbl_wordlist_path = ctk.CTkLabel(wl_frame, text="Varsayılan", text_color="white", font=("Roboto", 12, "italic"))
        self.lbl_wordlist_path.pack(side="left", padx=10)
        ctk.CTkButton(wl_frame, text="Dosya Seç", width=80, height=25, fg_color=COLORS["bg_input"], hover_color=COLORS["border"], text_color="white", command=self.select_wordlist).pack(side="right")
        self.selected_wordlist_path = None

        # 2. Araç Seçimleri
        tools_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Web Tarama Araçları", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.web_tools_vars = {
            "whois": ctk.BooleanVar(value=True), "dig": ctk.BooleanVar(value=True), "subfinder": ctk.BooleanVar(value=True),
            "nuclei": ctk.BooleanVar(value=True), "gobuster": ctk.BooleanVar(value=False), "sqlmap": ctk.BooleanVar(value=False)
        }
        
        grid_frm = ctk.CTkFrame(tools_frame, fg_color="transparent")
        grid_frm.pack(fill="x", padx=20, pady=10)
        r, c = 0, 0
        for tool, var in self.web_tools_vars.items():
            cb = ctk.CTkCheckBox(grid_frm, text=tool.title(), variable=var, text_color="white", fg_color=COLORS["accent"], border_color=COLORS["border"])
            cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
            c += 1
            if c > 3: 
                c = 0; r += 1

        # 3. Canlı Terminal ve Takip Barı
        self.progress_bar = ctk.CTkProgressBar(scroll, progress_color=COLORS["accent"])
        self.progress_bar.pack(fill="x", pady=(20, 5))
        self.progress_bar.set(0)
        
        term_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        term_frame.pack(fill="x", pady=(5, 10))
        ctk.CTkLabel(term_frame, text=">_ CANLI İŞLEM LOGLARI", font=("Consolas", 12, "bold"), text_color=COLORS["success"]).pack(anchor="w", padx=10, pady=(10, 0))
        self.terminal_box = ctk.CTkTextbox(term_frame, height=150, fg_color=COLORS["log_bg"], text_color=COLORS["terminal_fg"], font=("Consolas", 11))
        self.terminal_box.pack(fill="x", padx=10, pady=10)
        self.terminal_box.insert("0.0", "[*] Sistem hazır. Hedef girip taramayı başlatın...\n")

        # Başlat Butonu
        self.btn_web_launch = ctk.CTkButton(scroll, text="WEB TARAMASINI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=self.launch_scan)
        self.btn_web_launch.pack(fill="x", pady=20)

    def select_wordlist(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if path:
            self.selected_wordlist_path = path
            self.lbl_wordlist_path.configure(text=os.path.basename(path), text_color="white")

    def launch_scan(self):
        target = self.entry_web_domain.get().strip()
        if not target:
            self.terminal_box.insert("end", "[-] HATA: Lütfen geçerli bir Web Hedefi girin!\n")
            return

        self.btn_web_launch.configure(state="disabled", text="TARAMA VE ANALİZ DEVAM EDİYOR ⏳", fg_color=COLORS["warning"], text_color="black")
        self.progress_bar.set(0.1)
        self.terminal_box.insert("end", f"\n=====================================\n[*] YENİ WEB GÖREVİ: {target}\n")
        
        selected_tools = [tool for tool, var in self.web_tools_vars.items() if var.get()]
        
        scan_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.getcwd(), "scan_outputs", f"web_{scan_id}")
        
        # İşlemi Arka Plana Atıyoruz (Arayüz donmasın)
        threading.Thread(target=self._run_scan_thread, args=(target, output_dir, selected_tools), daemon=True).start()

    def _run_scan_thread(self, target, output_dir, selected_tools):
        def stream_callback(msg):
            self.terminal_box.insert("end", msg + "\n")
            self.terminal_box.see("end")

        try:
            self.progress_bar.set(0.3)
            # 1. Aşama: Web Araçlarını Çalıştır
            run_web_tests(target, output_dir, selected_tools, self.selected_wordlist_path, stream_callback)
            self.progress_bar.set(0.7)
            
            # 2. Aşama: Yapay Zeka Raporlaması
            stream_callback("\n[*] AI Analizi başlatılıyor...")
            api_key = self.app.config.get("api_key", "")
            
            if not api_key:
                stream_callback("[-] UYARI: Gemini API Key eksik. Rapor oluşturulamadı!")
            else:
                report_path = generate_report(output_dir, target, api_key)
                if report_path:
                    stream_callback(f"[+] ISO 27001 Raporu oluşturuldu: pentest_raporu.json")
                else:
                    stream_callback("[-] AI Raporu oluşturulurken bir hata oluştu veya API Limiti aşıldı (Kota Dolu).")
            
            self.progress_bar.set(1.0)
            stream_callback("\n[+] GÖREV BAŞARIYLA TAMAMLANDI!")

        except Exception as e:
            stream_callback(f"\n[-] KRİTİK HATA: İşlem sırasında bir sorun oluştu: {str(e)}")
            self.progress_bar.set(0)
        finally:
            self.btn_web_launch.configure(state="normal", text="WEB TARAMASINI BAŞLAT 🚀", fg_color=COLORS["success"], text_color="white")