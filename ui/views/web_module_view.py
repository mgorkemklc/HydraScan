import queue
import customtkinter as ctk
import threading
from tkinter import filedialog, messagebox
import time
import os
from datetime import datetime
import database
from core.web_app_module import run_web_tests

# İlerleyen aşamalarda core katmanını bağlayacağız
# from core.web_app_module import run_web_tests

COLORS = {
    "bg_panel": "#1e293b", "bg_input": "#334155", "accent": "#38bdf8", 
    "success": "#22c55e", "danger": "#ef4444", "text_gray": "#94a3b8"
}

class WebModuleView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.custom_wordlist_path = None
        self.build_ui()
        self.log_queue = queue.Queue()
        self.process_queue()

    def process_queue(self):
        # Arka plandan gelen logları güvenli şekilde arayüze basar
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_textbox.configure(state="normal")
                self.log_textbox.insert("end", msg + "\n")
                self.log_textbox.see("end")
                self.log_textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.process_queue) # Saniyede 10 kere kontrol et

    def build_ui(self):
        # Kaydırılabilir ana alan
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll, text="🌐 Web Uygulama Sızma Testi", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # --- Hedef Belirleme Alanı ---
        target_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        target_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(target_frame, text="Hedef Tanımlama", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.entry_target = ctk.CTkEntry(target_frame, placeholder_text="örn: https://target-web.com", height=45, fg_color=COLORS["bg_input"], border_width=0)
        self.entry_target.pack(fill="x", padx=20, pady=(0, 10))

        # --- Özel Wordlist Seçimi ---
        wl_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
        wl_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.btn_wordlist = ctk.CTkButton(wl_frame, text="Özel Wordlist Seç (Opsiyonel)", fg_color=COLORS["bg_input"], text_color="white", command=self.select_wordlist)
        self.btn_wordlist.pack(side="left")
        self.lbl_wordlist = ctk.CTkLabel(wl_frame, text="Seçilmedi (Varsayılan kullanılacak)", text_color=COLORS["text_gray"])
        self.lbl_wordlist.pack(side="left", padx=10)

        # --- Araç Seçimi Alanı ---
        tools_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Aktif Keşif ve Zafiyet Tarama Araçları", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))

        # Eski ve yeni araçların birleştirilmiş listesi
        self.tools_list = {
            "Keşif & Fuzzing": ["gobuster", "ffuf", "dirsearch", "amass", "subfinder"],
            "Zafiyet Tarama": ["nuclei", "nikto", "wapiti", "wpscan"],
            "Exploitation (Sömürü)": ["sqlmap", "dalfox", "xsstrike", "commix"]
        }
        
        self.checkbox_vars = {}
        
        for category, tools in self.tools_list.items():
            cat_frame = ctk.CTkFrame(tools_frame, fg_color="transparent")
            cat_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(cat_frame, text=category, font=("Roboto", 14, "bold"), text_color="white").pack(anchor="w")
            
            grid_frame = ctk.CTkFrame(cat_frame, fg_color="transparent")
            grid_frame.pack(fill="x", pady=5)
            
            r, c = 0, 0
            for tool in tools:
                # Varsayılan olarak temel araçları seçili getir
                default_state = True if tool in ["nuclei", "gobuster", "subfinder"] else False
                var = ctk.BooleanVar(value=default_state)
                self.checkbox_vars[tool] = var
                cb = ctk.CTkCheckBox(grid_frame, text=tool.upper(), variable=var, text_color="white")
                cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
                c += 1
                if c > 4:  # Her satırda 5 araç
                    c = 0
                    r += 1

        # --- Başlat Butonu ---
        self.btn_start = ctk.CTkButton(self.scroll, text="Taramayı Başlat", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], command=self.start_scan_thread)
        self.btn_start.pack(fill="x", pady=20)

        # --- Canlı Log Konsolu ---
        log_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        log_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(log_frame, text="İşlem Çıktısı (Log)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 0))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, height=200, fg_color=COLORS["bg_input"], text_color="#a3e635", font=("Consolas", 12))
        self.log_textbox.pack(fill="x", padx=20, pady=15)
        self.log_textbox.configure(state="disabled")

    def select_wordlist(self):
        filepath = filedialog.askopenfilename(title="Wordlist Seç", filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        if filepath:
            self.custom_wordlist_path = filepath
            self.lbl_wordlist.configure(text=filepath.split('/')[-1])

    def append_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_scan_thread(self):
        target = self.entry_target.get().strip()
        if not target:
            messagebox.showerror("Hata", "Lütfen bir hedef belirtin!")
            return

        selected_tools = [tool for tool, var in self.checkbox_vars.items() if var.get()]
        if not selected_tools:
            messagebox.showerror("Hata", "En az bir araç seçmelisiniz!")
            return

        self.btn_start.configure(state="disabled", text="Tarama Devam Ediyor...", fg_color=COLORS["text_gray"])
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        self.append_log(f"[*] Hedef: {target}")
        self.append_log(f"[*] Seçilen Araçlar: {', '.join(selected_tools)}")
        self.append_log("[*] Tarama başlatılıyor...\n")

        # İşlemi arayüzü dondurmamak için thread içinde başlatıyoruz
        threading.Thread(target=self.run_scan, args=(target, selected_tools), daemon=True).start()

    def run_scan(self, target, selected_tools):
        try:
            # 1. Veritabanında tarama kaydı oluştur
            scan_data = {
                "domain": target,
                "internal_ip": None,
                "apk_path": None
            }
            scan_id = database.create_scan(scan_data, self.controller.current_user.get('id', 1))
            self.append_log(f"[*] Tarama ID: {scan_id} oluşturuldu.")

            # 2. Çıktı klasörünü ayarla
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")
            database.set_scan_output_directory(scan_id, output_dir)
           
            # 3. Gerçek tarama motorunu (Core) çalıştır
            self.append_log(f"[*] Çıktı Dizini: {output_dir}")
            database.update_scan_status(scan_id, "RUNNING")

            
            # self.append_log YERİNE self.log_queue KULLANIYORUZ
            success = run_web_tests(
                domain_input=target,
                output_dir=output_dir,
                image_name="pentest-araci-kali:v1.5",
                selected_tools=selected_tools,
                stream_queue=self.log_queue, # BURASI DEĞİŞTİ
                custom_wordlist=self.custom_wordlist_path
            )

            # 4. İşlem bitince durumu güncelle
            if success:
                database.update_scan_status(scan_id, "COMPLETED")
                self.append_log("\n[!] Tarama bitti. Raporlar sekmesinden sonuçları inceleyebilirsiniz.")
                
        except Exception as e:
            self.append_log(f"\n[!] KRİTİK HATA: {str(e)}")
            try:
                database.update_scan_status(scan_id, "FAILED")
            except:
                pass
        finally:
            self.btn_start.configure(state="normal", text="Taramayı Başlat", fg_color=COLORS["success"])