import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import datetime
import threading
import json
import concurrent.futures
import logging

# --- MODÜLLER ---
import database
from core import recon_module, web_app_module, api_module, internal_network_module, report_module, mobile_module

# --- CONFIG & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
CONFIG_FILE = "config.json"

# --- TASARIM SABİTLERİ (Görseldeki Renkler) ---
COLORS = {
    "bg_main": "#0f172a",       # Slate 900
    "bg_panel": "#1e293b",      # Slate 800
    "bg_input": "#334155",      # Slate 700
    "accent": "#38bdf8",        # Sky 400
    "accent_hover": "#0ea5e9",  # Sky 500
    "text_white": "#f1f5f9",    # Slate 100
    "text_gray": "#94a3b8",     # Slate 400
    "danger": "#ef4444",        # Red 500
    "success": "#22c55e",       # Green 500
    "warning": "#f59e0b",       # Amber 500
    "running": "#3b82f6",       # Blue 500
    "border": "#334155"         # Slate 700
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- YARDIMCI SINIFLAR ---
class MetricCard(ctk.CTkFrame):
    """Dashboard üstündeki istatistik kartları"""
    def __init__(self, parent, title, value, sub_text, icon, icon_color):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(1, weight=1)
        
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 13), text_color=COLORS["text_gray"])
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=(20, 0), pady=(20, 5))
        
        self.lbl_value = ctk.CTkLabel(self, text=value, font=("Roboto", 32, "bold"), text_color="white")
        self.lbl_value.grid(row=1, column=0, sticky="w", padx=(20, 0), pady=(0, 5))
        
        self.lbl_sub = ctk.CTkLabel(self, text=sub_text, font=("Roboto", 11), text_color=icon_color)
        self.lbl_sub.grid(row=2, column=0, sticky="w", padx=(20, 0), pady=(0, 20))

        self.icon_frame = ctk.CTkFrame(self, width=45, height=45, corner_radius=10, fg_color=COLORS["bg_main"])
        self.icon_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=20, sticky="ne")
        
        # İkonu ortalamak için place kullanıyoruz (container içinde sorun olmaz)
        ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 20), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform")
        self.geometry("1400x900")
        self.configure(fg_color=COLORS["bg_main"])
        
        # Veritabanını başlat (User tablosu yoksa oluşturur)
        database.init_db()
        self.load_config()
        self.current_user = None 

        # Ana Konteyner
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

        # Login Ekranı ile Başla
        self.show_login_screen()

    def load_config(self):
        self.config = {"api_key": "", "theme": "Dark"}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config.update(json.load(f))
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f)

    # ==================================================================
    # LOGIN & LOGOUT (GİRİŞ SİSTEMİ) - DÜZELTİLDİ
    # ==================================================================
    def show_login_screen(self):
        """Giriş ekranını gösterir."""
        for widget in self.container.winfo_children(): widget.destroy()
        
        # DÜZELTME BURADA: width ve height parametrelerini constructor içine taşıdık
        login_frame = ctk.CTkFrame(
            self.container, 
            fg_color=COLORS["bg_panel"], 
            corner_radius=20, 
            border_width=1, 
            border_color=COLORS["border"],
            width=400,  # <-- Buraya taşındı
            height=500  # <-- Buraya taşındı
        )
        # place metodundan width/height kaldırıldı
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Frame boyutunu sabitlemek için pack_propagate kapatılabilir (isteğe bağlı)
        # login_frame.pack_propagate(False) 

        # Logo ve Başlık
        ctk.CTkLabel(login_frame, text="🐉", font=("Arial", 60)).pack(pady=(50, 10))
        ctk.CTkLabel(login_frame, text="HYDRASCAN", font=("Roboto", 28, "bold"), text_color="white").pack()
        ctk.CTkLabel(login_frame, text="Güvenli Giriş", font=("Roboto", 14), text_color=COLORS["accent"]).pack(pady=(0, 40))

        # Kullanıcı Adı
        self.entry_user = ctk.CTkEntry(login_frame, placeholder_text="Kullanıcı Adı", height=50, 
                                       fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_user.pack(fill="x", padx=40, pady=10)

        # Şifre
        self.entry_pass = ctk.CTkEntry(login_frame, placeholder_text="Şifre", show="*", height=50, 
                                       fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_pass.pack(fill="x", padx=40, pady=10)

        # Giriş Butonu
        ctk.CTkButton(login_frame, text="GİRİŞ YAP", height=50, fg_color=COLORS["accent"], 
                      hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"], 
                      font=("Roboto", 15, "bold"), command=self.login).pack(fill="x", padx=40, pady=40)
        
        # Varsayılan Bilgi
        ctk.CTkLabel(login_frame, text="Default: admin / admin123", text_color=COLORS["text_gray"], font=("Roboto", 11)).pack(side="bottom", pady=20)

    def login(self):
        username = self.entry_user.get()
        password = self.entry_pass.get()
        
        # Database kontrolü
        user = database.login_check(username, password)
        if user:
            self.current_user = user
            self.init_main_interface() # Başarılıysa ana ekrana geç
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı!")

    def logout(self):
        if messagebox.askyesno("Çıkış", "Oturumu kapatmak istiyor musunuz?"):
            self.current_user = None
            self.show_login_screen()

    # ==================================================================
    # ANA ARAYÜZ (SIDEBAR + CONTENT)
    # ==================================================================
    def init_main_interface(self):
        for widget in self.container.winfo_children(): widget.destroy()

        # Layout: Sidebar (Sol) + Main Content (Sağ)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        
        self.main_area = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)

        # Header (Üst Arama Çubuğu)
        self.create_header()

        # Sayfaları Hazırla
        self.frames = {}
        self.create_dashboard_view()
        self.create_new_scan_view()
        self.create_reports_view()
        self.create_settings_view()

        # İlk Açılış
        self.show_view("Dashboard")

    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self.container, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)

        # Logo Alanı
        logo_frm = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frm.pack(pady=(30, 40), padx=20, anchor="w")
        ctk.CTkLabel(logo_frm, text="🐉", font=("Arial", 30)).pack(side="left")
        ctk.CTkLabel(logo_frm, text=" HYDRA", font=("Roboto", 22, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(logo_frm, text="SCAN", font=("Roboto", 22, "bold"), text_color=COLORS["accent"]).pack(side="left")

        # Navigasyon Butonları
        self.nav_btns = {}
        self.add_nav_btn(sidebar, "Genel Bakış", "📊", "Dashboard")
        self.add_nav_btn(sidebar, "Yeni Tarama", "⌖", "NewScan")
        self.add_nav_btn(sidebar, "Raporlar & Loglar", "📄", "Reports")
        
        ctk.CTkLabel(sidebar, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(30, 10))
        self.add_nav_btn(sidebar, "Ayarlar", "⚙️", "Settings")

        # Profil ve Çıkış
        profile = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        
        # Kullanıcı baş harfleri
        initials = self.current_user['username'][:2].upper() if self.current_user else "U"
        
        avt = ctk.CTkLabel(profile, text=initials, width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold"))
        avt.pack(side="left", padx=15, pady=10)
        
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=self.current_user['username'], font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text=self.current_user['role'].upper(), font=("Roboto", 10), text_color=COLORS["text_gray"]).pack(anchor="w")

        # Çıkış Butonu
        ctk.CTkButton(profile, text="🚪", width=30, fg_color="transparent", hover_color=COLORS["bg_panel"], text_color=COLORS["danger"], font=("Arial", 20), command=self.logout).pack(side="right", padx=10)

    def add_nav_btn(self, parent, text, icon, view_name):
        btn = ctk.CTkButton(parent, text=f"  {icon}   {text}", anchor="w",
                            fg_color="transparent", text_color=COLORS["text_gray"],
                            hover_color=COLORS["bg_main"], height=45, font=("Roboto", 14),
                            command=lambda: self.show_view(view_name))
        btn.pack(fill="x", padx=15, pady=2)
        self.nav_btns[view_name] = btn

    def create_header(self):
        header = ctk.CTkFrame(self.main_area, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        self.page_title = ctk.CTkLabel(header, text="Genel Bakış", font=("Roboto", 24, "bold"), text_color="white")
        self.page_title.pack(side="left")

        # Arama Çubuğu
        search_frame = ctk.CTkFrame(header, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        search_frame.pack(side="right", padx=10)
        ctk.CTkLabel(search_frame, text="🔍", text_color=COLORS["text_gray"]).pack(side="left", padx=(15, 5))
        ctk.CTkEntry(search_frame, placeholder_text="IP, Domain veya Scan ID...", fg_color="transparent", border_width=0, width=250, text_color="white").pack(side="left", padx=(0, 10))

    def show_view(self, name):
        for frame in self.frames.values(): frame.grid_forget()
        
        if name in self.frames:
            self.frames[name].grid(row=1, column=0, sticky="nsew")
            
            # Başlık Güncelle
            titles = {"Dashboard": "Genel Bakış", "NewScan": "Yeni Tarama Başlat", "Reports": "Rapor Arşivi", "Settings": "Ayarlar", "ReportView": "Detaylı Rapor"}
            self.page_title.configure(text=titles.get(name, name))
            
            if name == "Dashboard": self.refresh_dashboard()
            if name == "Reports": self.refresh_reports_list()

            # Menü Aktifliği
            for btn_name, btn in self.nav_btns.items():
                if btn_name == name:
                    btn.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])
                else:
                    btn.configure(fg_color="transparent", text_color=COLORS["text_gray"])

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Dashboard"] = view
        
        # Kartlar
        cards = ctk.CTkFrame(view, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 30))
        self.card_total = MetricCard(cards, "Toplam Tarama", "0", "Arşivde", "🗃️", COLORS["accent"])
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.card_risk = MetricCard(cards, "Başarısız", "0", "Hata veya İptal", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=10)
        self.card_active = MetricCard(cards, "Aktif Görevler", "0", "Şu an çalışıyor", "⏳", COLORS["warning"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Tablo Alanı
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
        
        total = len(scans)
        active = sum(1 for s in scans if s['status'] in ["RUNNING", "REPORTING"])
        failed = sum(1 for s in scans if s['status'] == "FAILED")
        
        self.card_total.lbl_value.configure(text=str(total))
        self.card_active.lbl_value.configure(text=str(active))
        self.card_risk.lbl_value.configure(text=str(failed))

        for i in self.tree.get_children(): self.tree.delete(i)
        for s in scans[:10]:
            self.insert_scan_to_tree(self.tree, s)

    # ==================================================================
    # RAPORLAR (ARŞİV)
    # ==================================================================
    def create_reports_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Reports"] = view

        filter_bar = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], height=60, corner_radius=10)
        filter_bar.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(filter_bar, text="Arşiv Filtrele:", text_color=COLORS["text_gray"]).pack(side="left", padx=20)
        self.entry_search = ctk.CTkEntry(filter_bar, placeholder_text="Domain ara...", width=300, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.entry_search.pack(side="left", padx=10)
        ctk.CTkButton(filter_bar, text="Ara", width=80, command=self.refresh_reports_list, fg_color=COLORS["accent"], text_color=COLORS["bg_main"]).pack(side="left")

        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        cont.pack(fill="both", expand=True)
        
        self.reports_tree = self.create_treeview(cont)
        self.reports_tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.reports_tree.bind("<Double-1>", self.on_report_click)

        btn_frm = ctk.CTkFrame(view, fg_color="transparent")
        btn_frm.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frm, text="Seçili Taramayı Sil", fg_color=COLORS["danger"], hover_color="#dc2626", command=self.delete_selected_scan).pack(side="right")

    def refresh_reports_list(self):
        user_id = self.current_user['id']
        search = self.entry_search.get().lower()
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
                messagebox.showinfo("Başarılı", "Kayıt silindi.")
            except Exception as e:
                messagebox.showerror("Hata", str(e))

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

        ctk.CTkButton(cont, text="Ayarları Kaydet", width=200, height=45, fg_color=COLORS["success"], hover_color="#16a34a", 
                      font=("Roboto", 14, "bold"), command=self.save_settings).pack(anchor="w", padx=40)

    def save_settings(self):
        self.config["api_key"] = self.set_api.get()
        self.save_config()
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

    # ==================================================================
    # YENİ TARAMA & ÇALIŞTIRMA
    # ==================================================================
    def create_new_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["NewScan"] = view
        
        container = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        container.pack(fill="both", expand=True)
        content = ctk.CTkFrame(container, fg_color="transparent")
        content.pack(padx=40, pady=40, fill="x")

        ctk.CTkLabel(content, text="Hedef Domain / IP", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.entry_domain = ctk.CTkEntry(content, placeholder_text="örn: example.com", height=50, border_color=COLORS["border"], fg_color=COLORS["bg_main"])
        self.entry_domain.pack(fill="x", pady=(10, 20))

        ctk.CTkLabel(content, text="Gemini API Anahtarı", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.entry_key = ctk.CTkEntry(content, placeholder_text="API Key...", show="*", height=50, border_color=COLORS["border"], fg_color=COLORS["bg_main"])
        self.entry_key.pack(fill="x", pady=(10, 20))
        if self.config.get("api_key"): self.entry_key.insert(0, self.config["api_key"])

        self.btn_launch = ctk.CTkButton(content, text="Taramayı Başlat", height=50, font=("Roboto", 16, "bold"), 
                                        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"],
                                        command=self.start_scan)
        self.btn_launch.pack(fill="x", pady=20)

    def start_scan(self):
        domain = self.entry_domain.get()
        key = self.entry_key.get()
        if not domain or not key:
            messagebox.showwarning("Hata", "Alanları doldurun.")
            return
            
        self.btn_launch.configure(state="disabled", text="Başlatılıyor...")
        
        scan_data = {"domain": domain, "gemini_key": key, "user_id": self.current_user['id']}
        scan_id = database.create_scan(scan_data, user_id=self.current_user['id'])
        
        threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data), daemon=True).start()
        self.after(1000, lambda: self.show_view("Dashboard"))
        self.btn_launch.configure(state="normal", text="Taramayı Başlat")
        self.entry_domain.delete(0, "end")

    def run_scan_logic(self, scan_id, data):
        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            img = "pentest-araci-kali:v1.5"
            dom = data['domain']
            
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fs = [ex.submit(recon_module.run_reconnaissance, dom, dom, img, out),
                      ex.submit(web_app_module.run_web_tests, dom, img, out)]
                for f in concurrent.futures.as_completed(fs): pass

            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            if path: database.complete_scan(scan_id, path, "COMPLETED")
            else: database.complete_scan(scan_id, None, "FAILED")
        except Exception as e:
            logging.error(e)
            database.complete_scan(scan_id, None, "FAILED")

    # ==================================================================
    # RAPOR DETAY GÖRÜNTÜLEME
    # ==================================================================
    def show_report_view(self, scan_id):
        if "ReportView" in self.frames: self.frames["ReportView"].destroy()
        
        scan = database.get_scan_by_id(scan_id)
        report_data = {}
        path = scan['report_file_path']
        if path and path.endswith(".html"): path = path.replace(".html", ".json")
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: report_data = json.load(f)

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
                self.create_report_card(scroll, analiz)
        else:
            ctk.CTkLabel(view, text="Rapor verisi yok.").pack(pady=50)

        self.show_view("ReportView")

    def create_report_card(self, parent, analiz):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=10)
        
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=15)
        
        risk = analiz.get("risk_seviyesi", "").upper()
        col = COLORS["success"]
        if "KRITIK" in risk or "YÜKSEK" in risk: col = COLORS["danger"]
        elif "ORTA" in risk: col = COLORS["warning"]

        ctk.CTkLabel(head, text=analiz.get("arac_adi"), font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
        ctk.CTkLabel(head, text=risk, text_color="white", fg_color=col, corner_radius=6, padx=8).pack(side="right")
        ctk.CTkLabel(card, text=analiz.get("ozet"), font=("Roboto", 13), text_color="white", wraplength=900, justify="left").pack(fill="x", padx=20, pady=(0, 15))

    # --- TABLO YARDIMCILARI ---
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
        d = scan['created_at'][:16]
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

    def cleanup_unfinished_scans(self):
        try:
            conn = database.get_db_connection()
            conn.cursor().execute("UPDATE scans SET status = 'FAILED' WHERE status IN ('RUNNING', 'REPORTING')")
            conn.commit()
            conn.close()
        except: pass

if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()