import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import datetime
import threading
import json
import concurrent.futures
import logging
import glob
from pathlib import Path

# --- MODÜLLER ---
import database
from core import recon_module, web_app_module, api_module, internal_network_module, report_module, mobile_module

# --- CONFIG & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GÜVENLİK AYARI
USER_HOME = os.path.expanduser("~")
APP_DIR = os.path.join(USER_HOME, ".hydrascan")
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# --- RENKLER ---
COLORS = {
    "bg_main": "#0f172a", "bg_panel": "#1e293b", "bg_input": "#334155",
    "accent": "#38bdf8", "accent_hover": "#0ea5e9",
    "text_white": "#f1f5f9", "text_gray": "#94a3b8",
    "danger": "#ef4444", "success": "#22c55e", "warning": "#f59e0b",
    "running": "#3b82f6", "border": "#334155", "log_bg": "#0d1117"
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- YARDIMCI SINIFLAR ---
class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, sub_text, icon, icon_color):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text=title, font=("Roboto", 13), text_color=COLORS["text_gray"]).grid(row=0, column=0, sticky="w", padx=(20, 0), pady=(20, 5))
        self.lbl_value = ctk.CTkLabel(self, text=value, font=("Roboto", 32, "bold"), text_color="white")
        self.lbl_value.grid(row=1, column=0, sticky="w", padx=(20, 0), pady=(0, 5))
        ctk.CTkLabel(self, text=sub_text, font=("Roboto", 11), text_color=icon_color).grid(row=2, column=0, sticky="w", padx=(20, 0), pady=(0, 20))

        self.icon_frame = ctk.CTkFrame(self, width=45, height=45, corner_radius=10, fg_color=COLORS["bg_main"])
        self.icon_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=20, sticky="ne")
        ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 20), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

class ScanOptionCard(ctk.CTkFrame):
    def __init__(self, parent, title, description, icon, value, variable):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=2, border_color=COLORS["bg_panel"])
        self.value = value
        self.variable = variable
        self.bind("<Button-1>", self.select)
        
        self.lbl_icon = ctk.CTkLabel(self, text=icon, font=("Arial", 32), text_color=COLORS["accent"])
        self.lbl_icon.pack(pady=(20, 10))
        self.lbl_icon.bind("<Button-1>", self.select)
        
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 16, "bold"), text_color="white")
        self.lbl_title.pack(pady=(0, 5))
        self.lbl_title.bind("<Button-1>", self.select)
        
        self.lbl_desc = ctk.CTkLabel(self, text=description, font=("Roboto", 11), text_color=COLORS["text_gray"], wraplength=180)
        self.lbl_desc.pack(pady=(0, 20), padx=10)
        self.lbl_desc.bind("<Button-1>", self.select)

        if self.variable: self.variable.trace_add("write", self.update_state)

    def select(self, event=None):
        if self.variable: self.variable.set(self.value)

    def update_state(self, *args):
        if self.variable.get() == self.value:
            self.configure(border_color=COLORS["accent"], fg_color=COLORS["bg_input"])
        else:
            self.configure(border_color=COLORS["bg_panel"], fg_color=COLORS["bg_panel"])

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform")
        self.geometry("1400x900")
        self.configure(fg_color=COLORS["bg_main"])
        
        database.init_db()
        self.load_config()
        self.current_user = None 

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        self.show_login_screen()

    def load_config(self):
        self.config = {"api_key": "", "theme": "Dark"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except:
                pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f)

    # ==================================================================
    # LOGIN & REGISTER
    # ==================================================================
    def show_login_screen(self):
        for w in self.container.winfo_children(): w.destroy()
        
        frame = ctk.CTkFrame(self.container, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"], width=400, height=500)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(frame, text="🐉", font=("Arial", 60)).pack(pady=(40, 10))
        ctk.CTkLabel(frame, text="HYDRASCAN", font=("Roboto", 28, "bold"), text_color="white").pack()
        ctk.CTkLabel(frame, text="Kurumsal Güvenlik Girişi", font=("Roboto", 14), text_color=COLORS["accent"]).pack(pady=(0, 30))

        self.entry_user = ctk.CTkEntry(frame, placeholder_text="Kullanıcı Adı", height=50, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_user.pack(fill="x", padx=40, pady=10)
        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="Şifre", show="*", height=50, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_pass.pack(fill="x", padx=40, pady=10)

        ctk.CTkButton(frame, text="GİRİŞ YAP", height=50, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"], font=("Roboto", 15, "bold"), command=self.login).pack(fill="x", padx=40, pady=20)
        
        reg_frame = ctk.CTkFrame(frame, fg_color="transparent")
        reg_frame.pack(pady=10)
        ctk.CTkLabel(reg_frame, text="Erişiminiz yok mu?", text_color=COLORS["text_gray"], font=("Roboto", 12)).pack(side="left")
        ctk.CTkButton(reg_frame, text="Kayıt Olun", fg_color="transparent", text_color=COLORS["accent"], width=60, hover=False, font=("Roboto", 12, "bold"), command=self.show_register_screen).pack(side="left")

    def show_register_screen(self):
        for w in self.container.winfo_children(): w.destroy()
        
        frame = ctk.CTkFrame(self.container, fg_color=COLORS["bg_panel"], corner_radius=20, width=400, height=550)
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(frame, text="👤", font=("Arial", 60)).pack(pady=(40, 10))
        ctk.CTkLabel(frame, text="YENİ HESAP", font=("Roboto", 24, "bold"), text_color="white").pack(pady=(0, 30))

        self.reg_user = ctk.CTkEntry(frame, placeholder_text="Kullanıcı Adı", height=50, fg_color=COLORS["bg_main"])
        self.reg_user.pack(fill="x", padx=40, pady=10)
        self.reg_pass = ctk.CTkEntry(frame, placeholder_text="Şifre", show="*", height=50, fg_color=COLORS["bg_main"])
        self.reg_pass.pack(fill="x", padx=40, pady=10)

        ctk.CTkButton(frame, text="KAYDI TAMAMLA", height=50, fg_color=COLORS["success"], hover_color="#16a34a", text_color="white", font=("Roboto", 15, "bold"), command=self.register).pack(fill="x", padx=40, pady=20)
        ctk.CTkButton(frame, text="Girişe Dön", fg_color="transparent", text_color=COLORS["text_gray"], command=self.show_login_screen).pack(pady=10)

    def login(self):
        user = database.login_check(self.entry_user.get(), self.entry_pass.get())
        if user:
            self.current_user = user
            self.sync_filesystem_to_db() 
            self.init_main_interface()
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı!")

    def register(self):
        u, p = self.reg_user.get(), self.reg_pass.get()
        if not u or not p: return messagebox.showwarning("Eksik", "Bilgileri doldurun.")
        if database.register_user(u, p):
            messagebox.showinfo("Başarılı", "Kayıt oluşturuldu! Giriş yapabilirsiniz.")
            self.show_login_screen()
        else:
            messagebox.showerror("Hata", "Kullanıcı adı alınmış.")

    def logout(self):
        if messagebox.askyesno("Çıkış", "Oturumu kapat?"):
            self.current_user = None
            self.show_login_screen()

    # ==================================================================
    # SYNC
    # ==================================================================
    def sync_filesystem_to_db(self):
        if not os.path.exists("scan_outputs"): return
        
        print("[*] Eski taramalar senkronize ediliyor...")
        scan_dirs = glob.glob("scan_outputs/scan_*")
        
        for d in scan_dirs:
            report_path = None
            json_files = glob.glob(os.path.join(d, "*.json"))
            if json_files: report_path = json_files[0]
            
            if report_path:
                timestamp = os.path.getctime(report_path)
                date_obj = datetime.datetime.fromtimestamp(timestamp)
                domain_name = "Bilinmeyen Hedef"
                
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        domain_name = data.get("domain", "Bilinmeyen Hedef")
                except: pass
                
                database.insert_imported_scan(
                    self.current_user['id'], domain_name, "COMPLETED", 
                    os.path.abspath(d), os.path.abspath(report_path), date_obj
                )

    # ==================================================================
    # ANA ARAYÜZ
    # ==================================================================
    def init_main_interface(self):
        for w in self.container.winfo_children(): w.destroy()
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.main_area = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.frames = {}
        self.create_dashboard_view()
        self.create_new_scan_view()
        self.create_reports_view()
        self.create_settings_view()
        self.show_view("Dashboard")

    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self.container, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)

        logo_frm = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frm.pack(pady=(30, 40), padx=20, anchor="w")
        ctk.CTkLabel(logo_frm, text="🐉", font=("Arial", 30)).pack(side="left")
        ctk.CTkLabel(logo_frm, text=" HYDRA", font=("Roboto", 22, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(logo_frm, text="SCAN", font=("Roboto", 22, "bold"), text_color=COLORS["accent"]).pack(side="left")

        self.nav_btns = {}
        self.add_nav_btn(sidebar, "Genel Bakış", "📊", "Dashboard")
        self.add_nav_btn(sidebar, "Yeni Tarama", "⌖", "NewScan")
        self.add_nav_btn(sidebar, "Raporlar & Loglar", "📄", "Reports")
        
        ctk.CTkLabel(sidebar, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(30, 10))
        self.add_nav_btn(sidebar, "Ayarlar", "⚙️", "Settings")

        profile = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        initials = self.current_user['username'][:2].upper()
        ctk.CTkLabel(profile, text=initials, width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=10)
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=self.current_user['username'], font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text="Admin", font=("Roboto", 10), text_color=COLORS["text_gray"]).pack(anchor="w")
        ctk.CTkButton(profile, text="🚪", width=30, fg_color="transparent", text_color=COLORS["danger"], font=("Arial", 16), command=self.logout).pack(side="right", padx=10)

    def add_nav_btn(self, parent, text, icon, view_name):
        btn = ctk.CTkButton(parent, text=f"  {icon}   {text}", anchor="w", fg_color="transparent", text_color=COLORS["text_gray"], hover_color=COLORS["bg_main"], height=45, font=("Roboto", 14), command=lambda: self.show_view(view_name))
        btn.pack(fill="x", padx=15, pady=2)
        self.nav_btns[view_name] = btn

    def create_header(self):
        header = ctk.CTkFrame(self.main_area, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.page_title = ctk.CTkLabel(header, text="Genel Bakış", font=("Roboto", 24, "bold"), text_color="white")
        self.page_title.pack(side="left")
        
        search_frame = ctk.CTkFrame(header, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        search_frame.pack(side="right", padx=10)
        ctk.CTkLabel(search_frame, text="🔍", text_color=COLORS["text_gray"]).pack(side="left", padx=(15, 5))
        self.global_search = ctk.CTkEntry(search_frame, placeholder_text="Taramalarda ara...", fg_color="transparent", border_width=0, width=250, text_color="white")
        self.global_search.pack(side="left", padx=(0, 10))
        self.global_search.bind("<Return>", self.perform_global_search)

    def perform_global_search(self, event=None):
        query = self.global_search.get()
        if query:
            self.show_view("Reports")
            self.entry_search_reports.delete(0, "end")
            self.entry_search_reports.insert(0, query)
            self.refresh_reports_list()

    def show_view(self, name):
        for frame in self.frames.values(): frame.grid_forget()
        self.frames[name].grid(row=1, column=0, sticky="nsew")
        self.page_title.configure(text={"Dashboard": "Genel Bakış", "NewScan": "Yeni Tarama Başlat", "Reports": "Rapor Arşivi", "Settings": "Ayarlar", "ReportView": "Detaylı Rapor"}.get(name, name))
        if name == "Dashboard": self.refresh_dashboard()
        if name == "Reports": self.refresh_reports_list()
        for n, b in self.nav_btns.items():
            b.configure(fg_color=COLORS["bg_main"] if n == name else "transparent", text_color=COLORS["accent"] if n == name else COLORS["text_gray"])

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Dashboard"] = view
        
        cards = ctk.CTkFrame(view, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 30))
        self.card_total = MetricCard(cards, "Toplam Tarama", "0", "Arşivde", "🗃️", COLORS["accent"])
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.card_active = MetricCard(cards, "Aktif Görevler", "0", "Şu an çalışıyor", "⏳", COLORS["warning"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=10)
        self.card_risk = MetricCard(cards, "Başarısız/Risk", "0", "İncelenmeli", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=(10, 0))

        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        cont.pack(fill="both", expand=True)
        head = ctk.CTkFrame(cont, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(head, text="Son Aktiviteler", font=("Roboto", 18, "bold"), text_color="white").pack(side="left")
        ctk.CTkButton(head, text="+ Yeni Tarama", width=120, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"], command=lambda: self.show_view("NewScan")).pack(side="right")
        
        self.tree = self.create_treeview(cont)
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tree.bind("<Double-1>", self.on_dashboard_click)

    def refresh_dashboard(self):
        user_id = self.current_user['id']
        scans = database.get_all_scans(user_id) 
        self.card_total.lbl_value.configure(text=str(len(scans)))
        self.card_active.lbl_value.configure(text=str(sum(1 for s in scans if s['status'] in ["RUNNING", "REPORTING"])))
        self.card_risk.lbl_value.configure(text=str(sum(1 for s in scans if s['status'] == "FAILED")))
        for i in self.tree.get_children(): self.tree.delete(i)
        for s in scans[:10]: self.insert_scan_to_tree(self.tree, s)

    # ==================================================================
    # YENİ TARAMA (GÜNCELLENDİ: MODÜLER SEÇİM + APK)
    # ==================================================================
    def create_new_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["NewScan"] = view
        
        scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Yeni Tarama Yapılandırması", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # --- 1. HEDEF BİLGİLERİ ---
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, text="Hedef Tanımları", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.entry_domain = ctk.CTkEntry(info_frame, placeholder_text="Domain veya IP (örn: example.com)", height=45, border_color=COLORS["border"], fg_color=COLORS["bg_input"])
        self.entry_domain.pack(fill="x", padx=20, pady=(0, 15))

        self.entry_key = ctk.CTkEntry(info_frame, placeholder_text="Gemini API Anahtarı (Raporlama için)", height=45, border_color=COLORS["border"], fg_color=COLORS["bg_input"])
        self.entry_key.pack(fill="x", padx=20, pady=(0, 20))
        # Ayarlardan otomatik çek
        if self.config.get("api_key"): self.entry_key.insert(0, self.config["api_key"])

        # --- 2. ARAÇ SEÇİMİ (MODÜLER) ---
        tools_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(tools_frame, text="Aktif Tarama Araçları", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))

        # Checkbox Değişkenleri
        self.tools_vars = {
            "whois": ctk.BooleanVar(value=True),
            "dig": ctk.BooleanVar(value=True),
            "nmap": ctk.BooleanVar(value=True),
            "subfinder": ctk.BooleanVar(value=True),
            "amass": ctk.BooleanVar(value=False), # Yavaş olduğu için default kapalı
            "nuclei": ctk.BooleanVar(value=True), # Kritik
            "gobuster": ctk.BooleanVar(value=True),
            "sqlmap": ctk.BooleanVar(value=False),
            "dalfox": ctk.BooleanVar(value=False),
            "commix": ctk.BooleanVar(value=False),
            "wapiti": ctk.BooleanVar(value=False),
            "hydra": ctk.BooleanVar(value=False),
            "mobile": ctk.BooleanVar(value=False) # APK
        }

        # Grid yapısı ile araçları dizelim
        grid_frm = ctk.CTkFrame(tools_frame, fg_color="transparent")
        grid_frm.pack(fill="x", padx=20, pady=(0, 20))

        tools_list = [
            ("Whois (Keşif)", "whois"), ("Dig (DNS)", "dig"), ("Nmap (Port)", "nmap"),
            ("Subfinder (Subdomain)", "subfinder"), ("Amass (Derin Keşif)", "amass"),
            ("Nuclei (Modern Vuln)", "nuclei"), ("Gobuster (Dizin)", "gobuster"),
            ("SQLMap (SQLi)", "sqlmap"), ("Dalfox (XSS)", "dalfox"),
            ("Commix (Cmd Inj)", "commix"), ("Wapiti (Blackbox)", "wapiti"),
            ("Hydra (Brute Force)", "hydra")
        ]

        r, c = 0, 0
        for text, key in tools_list:
            cb = ctk.CTkCheckBox(grid_frm, text=text, variable=self.tools_vars[key], 
                                 text_color="white", fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"])
            cb.grid(row=r, column=c, sticky="w", padx=10, pady=10)
            c += 1
            if c > 3: # 4 sütun
                c = 0; r += 1

        # --- 3. MOBİL ANALİZ (ÖZEL ALAN) ---
        mobile_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10, border_color=COLORS["warning"], border_width=1)
        mobile_frame.pack(fill="x", pady=10)
        
        # Checkbox tetiklenince frame'i aç/kapat mantığı eklenebilir ama şimdilik direkt gösteriyoruz
        cb_mobile = ctk.CTkCheckBox(mobile_frame, text="Mobil Uygulama Analizi (APK / AAB)", variable=self.tools_vars["mobile"], 
                                    text_color=COLORS["warning"], fg_color=COLORS["warning"], command=self.toggle_apk_input)
        cb_mobile.pack(anchor="w", padx=20, pady=15)

        self.apk_input_frame = ctk.CTkFrame(mobile_frame, fg_color="transparent")
        # Başlangıçta gizli olmayacak, toggle fonksiyonu yönetecek
        
        self.lbl_apk_path = ctk.CTkLabel(self.apk_input_frame, text="Dosya seçilmedi", text_color=COLORS["text_gray"])
        self.lbl_apk_path.pack(side="left", padx=10)
        
        ctk.CTkButton(self.apk_input_frame, text="Dosya Yükle", width=100, command=self.select_apk, 
                      fg_color=COLORS["bg_input"], hover_color=COLORS["bg_main"]).pack(side="left")
        
        self.selected_apk_path = None

        # --- BAŞLAT ---
        self.progress_bar = ctk.CTkProgressBar(scroll, height=15, progress_color=COLORS["running"])
        self.progress_bar.set(0)
        self.lbl_status = ctk.CTkLabel(scroll, text="", text_color=COLORS["accent"])

        self.btn_launch = ctk.CTkButton(scroll, text="TARAMAYI BAŞLAT 🚀", height=50, 
                                        font=("Roboto", 16, "bold"), fg_color=COLORS["success"], 
                                        hover_color="#16a34a", command=self.start_scan)
        self.btn_launch.pack(fill="x", pady=20)

    def toggle_apk_input(self):
        """Mobil analiz seçilirse dosya yükleme alanını göster."""
        if self.tools_vars["mobile"].get():
            self.apk_input_frame.pack(fill="x", padx=40, pady=(0, 20))
        else:
            self.apk_input_frame.pack_forget()

    def select_apk(self):
        # BURASI GÜNCELLENDİ: .aab ve .xapk eklendi
        path = filedialog.askopenfilename(filetypes=[("Android Package", "*.apk *.aab *.xapk")])
        if path:
            self.selected_apk_path = path
            self.lbl_apk_path.configure(text=os.path.basename(path), text_color="white")

    def start_scan(self):
        domain = self.entry_domain.get()
        key = self.entry_key.get()
        
        # Hangi araçlar seçili?
        selected_tools = [key for key, var in self.tools_vars.items() if var.get()]
        
        if not domain or not key:
            messagebox.showwarning("Eksik", "Domain ve API Key zorunludur.")
            return
        
        if "mobile" in selected_tools and not self.selected_apk_path:
            messagebox.showwarning("Eksik", "Mobil analiz seçili ancak dosya yüklenmedi.")
            return

        # UI Kitleme
        self.btn_launch.configure(state="disabled", text="Sistemler Başlatılıyor...")
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        
        # Veritabanı Kayıt
        scan_data = {
            "domain": domain, 
            "gemini_key": key, 
            "apk_path": self.selected_apk_path if "mobile" in selected_tools else None
        }
        
        try:
            # User ID veritabanı yapısına göre eklendi
            scan_id = database.create_scan(scan_data, user_id=self.current_user['id'])
            
            # Thread Başlat (Seçili araçları da gönderiyoruz)
            threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data, selected_tools), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Başlatma hatası: {e}")
            self.reset_scan_ui()

    def run_scan_logic(self, scan_id, data, selected_tools):
        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            img = "pentest-araci-kali:v1.5" # İmaj isminiz
            dom = data['domain']
            
            # Paralel Çalıştırma
            with concurrent.futures.ThreadPoolExecutor() as ex:
                futures = []
                
                # Recon ve Web Modüllerine 'selected_tools' listesini gönderiyoruz
                futures.append(ex.submit(recon_module.run_reconnaissance, dom, out, img, selected_tools))
                futures.append(ex.submit(web_app_module.run_web_tests, dom, out, img, selected_tools))
                
                if "mobile" in selected_tools and data['apk_path']:
                    futures.append(ex.submit(mobile_module.run_mobile_tests, data['apk_path'], out, img))

                for f in concurrent.futures.as_completed(futures): pass

            # Raporlama
            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            status = "COMPLETED" if path else "FAILED"
            database.complete_scan(scan_id, path, status)
            
        except Exception as e:
            logging.error(f"Scan Error: {e}")
            database.complete_scan(scan_id, None, "FAILED")
        finally:
            self.after(0, self.reset_scan_ui)

    def reset_scan_ui(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.lbl_status.pack_forget()
        self.entry_domain.configure(state="normal")
        self.entry_key.configure(state="normal")
        self.entry_domain.delete(0, "end")
        self.btn_launch.configure(state="normal", text="Taramayı Başlat")
        self.show_view("Dashboard")
        messagebox.showinfo("Bitti", "Tarama işlemi tamamlandı.")

    # ==================================================================
    # RAPORLAR
    # ==================================================================
    def create_reports_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Reports"] = view

        filter_bar = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], height=60, corner_radius=10)
        filter_bar.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(filter_bar, text="Arşiv Filtrele:", text_color=COLORS["text_gray"]).pack(side="left", padx=20)
        self.entry_search_reports = ctk.CTkEntry(filter_bar, placeholder_text="Domain ara...", width=300, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.entry_search_reports.pack(side="left", padx=10)
        ctk.CTkButton(filter_bar, text="Ara / Yenile", width=120, command=self.refresh_reports_list, fg_color=COLORS["accent"], text_color=COLORS["bg_main"]).pack(side="left")

        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        cont.pack(fill="both", expand=True)
        self.reports_tree = self.create_treeview(cont)
        self.reports_tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.reports_tree.bind("<Double-1>", self.on_report_click)

        btn_frm = ctk.CTkFrame(view, fg_color="transparent")
        btn_frm.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frm, text="Seçili Taramayı Sil", fg_color=COLORS["danger"], hover_color="#dc2626", command=self.delete_selected_scan).pack(side="right")

    def refresh_reports_list(self):
        self.sync_filesystem_to_db()
        user_id = self.current_user['id']
        search = self.entry_search_reports.get().lower()
        scans = database.get_all_scans(user_id)
        for i in self.reports_tree.get_children(): self.reports_tree.delete(i)
        for s in scans:
            if search and search not in s['target_full_domain'].lower(): continue
            self.insert_scan_to_tree(self.reports_tree, s)

    def delete_selected_scan(self):
        sel = self.reports_tree.selection()
        if not sel: return
        sid = int(self.reports_tree.item(sel[0])['values'][0])
        if messagebox.askyesno("Sil", "Bu kaydı silmek istediğinize emin misiniz?"):
            scan = database.get_scan_by_id(sid)
            try:
                import shutil
                if scan['output_directory'] and os.path.exists(scan['output_directory']):
                    shutil.rmtree(scan['output_directory'])
                database.delete_scan_from_db(sid)
                self.refresh_reports_list()
            except Exception as e: messagebox.showerror("Hata", str(e))

    # ==================================================================
    # AYARLAR
    # ==================================================================
    def create_settings_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Settings"] = view
        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        cont.pack(fill="both", expand=True, padx=50, pady=20)
        ctk.CTkLabel(cont, text="Uygulama Ayarları", font=("Roboto", 20, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(40, 20))
        ctk.CTkLabel(cont, text="Varsayılan Gemini API Anahtarı", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(10, 5))
        self.set_api = ctk.CTkEntry(cont, placeholder_text="API Key...", width=500, height=45, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.set_api.pack(anchor="w", padx=40, pady=(0, 20))
        if "api_key" in self.config: self.set_api.insert(0, self.config["api_key"])
        ctk.CTkLabel(cont, text=f"Güvenli Config Yolu: {CONFIG_FILE}", text_color=COLORS["text_gray"], font=("Roboto", 10)).pack(anchor="w", padx=40)
        ctk.CTkButton(cont, text="Ayarları Kaydet", width=200, height=45, fg_color=COLORS["success"], hover_color="#16a34a", command=self.save_settings).pack(anchor="w", padx=40, pady=20)

    def save_settings(self):
        self.config["api_key"] = self.set_api.get()
        self.save_config()
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

    # ==================================================================
    # DETAY RAPOR & HAM ÇIKTI (Düzeltildi: Try-With Bloğu)
    # ==================================================================
    def show_report_view(self, scan_id):
        if "ReportView" in self.frames: self.frames["ReportView"].destroy()
        
        scan = database.get_scan_by_id(scan_id)
        report_data = {}
        path = scan['report_file_path']
        if path and path.endswith(".html"): path = path.replace(".html", ".json")
        
        # HATA DÜZELTİLDİ: Try ve with ayrıldı
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
            except Exception as e:
                logging.error(f"Rapor okuma hatası: {e}")

        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["ReportView"] = view
        
        top_bar = ctk.CTkFrame(view, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(top_bar, text="← Geri", width=80, fg_color=COLORS["bg_panel"], command=lambda: self.show_view("Dashboard")).pack(side="left")
        ctk.CTkLabel(top_bar, text=f"Rapor: {scan['target_full_domain']}", font=("Roboto", 20, "bold"), text_color="white").pack(side="left", padx=20)

        if report_data:
            scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            for analiz in report_data.get("analizler", []):
                self.create_report_card(scroll, analiz, scan_id)
        else:
            ctk.CTkLabel(view, text="Rapor verisi yok veya bozuk.", text_color=COLORS["danger"]).pack(pady=50)

        self.show_view("ReportView")

    def create_report_card(self, parent, analiz, scan_id):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=10)
        
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(head, text=analiz.get("arac_adi"), font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
        
        right_box = ctk.CTkFrame(head, fg_color="transparent")
        right_box.pack(side="right")
        
        ctk.CTkButton(right_box, text="📜 Ham Çıktı", width=100, height=28, 
                      fg_color=COLORS["bg_input"], hover_color=COLORS["bg_main"], 
                      font=("Roboto", 11),
                      command=lambda: self.view_raw_log(scan_id, analiz.get("arac_adi"))).pack(side="left", padx=(0, 10))

        risk = analiz.get("risk_seviyesi", "").upper()
        col = COLORS["success"]
        if "KRITIK" in risk or "YÜKSEK" in risk or "HATA" in risk: col = COLORS["danger"]
        elif "ORTA" in risk: col = COLORS["warning"]
        ctk.CTkLabel(right_box, text=risk, text_color="white", fg_color=col, corner_radius=6, padx=8).pack(side="left")
        
        ozet = analiz.get("ozet", "Veri yok")
        if "Quota exceeded" in ozet: ozet = "⚠️ Google API Kotası aşıldı."
        ctk.CTkLabel(card, text=ozet, font=("Roboto", 13), text_color="white", wraplength=900, justify="left").pack(fill="x", padx=20, pady=(0, 15))

    def view_raw_log(self, scan_id, tool_name):
        scan = database.get_scan_by_id(scan_id)
        out_dir = scan['output_directory']
        if not out_dir or not os.path.exists(out_dir):
            messagebox.showerror("Hata", "Log klasörü bulunamadı.")
            return

        safe_name = tool_name.lower().replace(" ", "_")
        filename = f"{safe_name}_ciktisi.txt"
        filepath = os.path.join(out_dir, filename)
        
        content = "Dosya bulunamadı."
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e: content = f"Okuma hatası: {e}"
        else:
            files = glob.glob(os.path.join(out_dir, f"*{safe_name}*.txt"))
            if files:
                try:
                    with open(files[0], 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except: pass

        log_win = ctk.CTkToplevel(self)
        log_win.title(f"Ham Çıktı: {tool_name}")
        log_win.geometry("900x600")
        log_win.configure(fg_color=COLORS["bg_main"])
        
        textbox = ctk.CTkTextbox(log_win, fg_color=COLORS["log_bg"], text_color="#00ff00", font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        textbox.insert("0.0", content)
        textbox.configure(state="disabled")

    def create_treeview(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["bg_main"], foreground="white", fieldbackground=COLORS["bg_main"], bordercolor=COLORS["bg_panel"], rowheight=45, font=("Roboto", 12))
        style.configure("Treeview.Heading", background=COLORS["bg_panel"], foreground=COLORS["text_gray"], font=("Roboto", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["bg_panel"])])
        tree = ttk.Treeview(parent, columns=("ID", "Target", "Status", "Date"), show="headings")
        tree.heading("ID", text="ID"); tree.column("ID", width=50, anchor="center")
        tree.heading("Target", text="HEDEF"); tree.column("Target", width=300)
        tree.heading("Status", text="DURUM"); tree.column("Status", width=150)
        tree.heading("Date", text="TARİH"); tree.column("Date", width=150, anchor="center")
        return tree

    def insert_scan_to_tree(self, tree, scan):
        st = scan['status']
        icon = "⏳" if st == "PENDING" else "⚡" if st == "RUNNING" else "✅" if st == "COMPLETED" else "❌"
        d = scan['created_at']
        if isinstance(d, str): d = d[:16]
        elif isinstance(d, datetime.datetime): d = d.strftime("%Y-%m-%d %H:%M")
        tree.insert("", "end", iid=scan['id'], values=(scan['id'], scan['target_full_domain'], f"{icon} {st}", d))

    def on_dashboard_click(self, event):
        sel = self.tree.selection()
        if sel:
            scan = database.get_scan_by_id(int(sel[0]))
            if scan['status'] == "COMPLETED": self.show_report_view(scan['id'])

    def on_report_click(self, event):
        sel = self.reports_tree.selection()
        if sel:
            scan = database.get_scan_by_id(int(sel[0]))
            if scan['status'] == "COMPLETED": self.show_report_view(scan['id'])

if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()