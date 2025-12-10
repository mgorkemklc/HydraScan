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

# GÜVENLİK AYARI: Config dosyasını proje klasöründen çıkarıp kullanıcı dizinine alıyoruz.
# Windows: C:\Users\Kullanici\.hydrascan\config.json
# Linux/Mac: /home/user/.hydrascan/config.json
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
    "running": "#3b82f6", "border": "#334155"
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MetricCard(ctk.CTkFrame):
    """Dashboard İstatistik Kartı"""
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
        ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 20), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform")
        self.geometry("1400x900")
        self.configure(fg_color=COLORS["bg_main"])
        
        database.init_db()
        self.load_config()
        self.current_user = None 

        # Ana Konteyner
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)

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
    # LOGIN & REGISTER
    # ==================================================================
    def show_login_screen(self):
        for w in self.container.winfo_children(): w.destroy()
        
        # Frame boyutlandırması ve ortalama
        frame = ctk.CTkFrame(
            self.container, 
            fg_color=COLORS["bg_panel"], 
            corner_radius=20, 
            border_width=1, 
            border_color=COLORS["border"],
            width=400,
            height=500
        )
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        ctk.CTkLabel(frame, text="🐉", font=("Arial", 60)).pack(pady=(40, 10))
        ctk.CTkLabel(frame, text="HYDRASCAN", font=("Roboto", 28, "bold"), text_color="white").pack()
        ctk.CTkLabel(frame, text="Kurumsal Güvenlik Girişi", font=("Roboto", 14), text_color=COLORS["accent"]).pack(pady=(0, 30))

        self.entry_user = ctk.CTkEntry(frame, placeholder_text="Kullanıcı Adı", height=50, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_user.pack(fill="x", padx=40, pady=10)

        self.entry_pass = ctk.CTkEntry(frame, placeholder_text="Şifre", show="*", height=50, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.entry_pass.pack(fill="x", padx=40, pady=10)

        ctk.CTkButton(frame, text="GİRİŞ YAP", height=50, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"], font=("Roboto", 15, "bold"), command=self.login).pack(fill="x", padx=40, pady=20)
        
        # Kayıt Ol Linki
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
            self.sync_filesystem_to_db() # Eski dosyaları tara ve ekle
            self.init_main_interface()
        else:
            messagebox.showerror("Hata", "Giriş başarısız!")

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
    # DOSYA SİSTEMİ SENKRONİZASYONU (ESKİ RAPORLARI GÖRME)
    # ==================================================================
    def sync_filesystem_to_db(self):
        """scan_outputs klasörünü tarar ve DB'de olmayan raporları ekler."""
        if not os.path.exists("scan_outputs"): return
        
        # Klasörleri gez
        scan_dirs = glob.glob("scan_outputs/scan_*")
        count = 0
        for d in scan_dirs:
            # Klasör içindeki rapor dosyasını bul (v2 html veya json)
            report_path = None
            json_files = glob.glob(os.path.join(d, "*.json"))
            html_files = glob.glob(os.path.join(d, "*.html"))
            
            # Öncelik JSON'da
            if json_files: report_path = json_files[0]
            elif html_files: report_path = html_files[0]
            
            if report_path:
                # Dosya oluşturulma tarihi
                timestamp = os.path.getctime(report_path)
                date_obj = datetime.datetime.fromtimestamp(timestamp)
                
                # Domain adını klasörden veya json'dan tahmin et
                domain_name = "Bilinmeyen Hedef"
                if report_path.endswith(".json"):
                    try:
                        with open(report_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            domain_name = data.get("domain", "Bilinmeyen")
                    except: pass
                
                # Veritabanına ekle (Eğer yoksa)
                database.insert_imported_scan(
                    self.current_user['id'], 
                    domain_name, 
                    "COMPLETED", 
                    os.path.abspath(d), 
                    os.path.abspath(report_path), 
                    date_obj
                )
                count += 1
        if count > 0:
            print(f"[Sync] {count} adet geçmiş tarama veritabanına eklendi.")

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
        
        # Arama Çubuğu (Fonksiyonel)
        search_frame = ctk.CTkFrame(header, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        search_frame.pack(side="right", padx=10)
        ctk.CTkLabel(search_frame, text="🔍", text_color=COLORS["text_gray"]).pack(side="left", padx=(15, 5))
        
        self.global_search = ctk.CTkEntry(search_frame, placeholder_text="Taramalarda ara...", fg_color="transparent", border_width=0, width=250, text_color="white")
        self.global_search.pack(side="left", padx=(0, 10))
        self.global_search.bind("<Return>", self.perform_global_search) # Enter'a basınca ara

    def perform_global_search(self, event=None):
        query = self.global_search.get()
        if query:
            self.show_view("Reports") # Raporlar sayfasına git
            self.entry_search_reports.delete(0, "end")
            self.entry_search_reports.insert(0, query)
            self.refresh_reports_list()

    def show_view(self, name):
        for frame in self.frames.values(): frame.grid_forget()
        self.frames[name].grid(row=1, column=0, sticky="nsew")
        self.page_title.configure(text={"Dashboard": "Genel Bakış", "NewScan": "Yeni Tarama Başlat", "Reports": "Rapor Arşivi", "Settings": "Ayarlar"}.get(name, name))
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
        self.card_risk = MetricCard(cards, "Başarısız", "0", "Hata veya İptal", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=10)
        self.card_active = MetricCard(cards, "Aktif Görevler", "0", "Şu an çalışıyor", "⏳", COLORS["warning"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=(10, 0))

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
    # YENİ TARAMA (GELİŞTİRİLDİ: Progress Bar & Locking)
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

        # Progress Bar (Gizli Başla)
        self.progress_bar = ctk.CTkProgressBar(content, height=15, progress_color=COLORS["running"])
        self.progress_bar.set(0)
        
        self.lbl_status = ctk.CTkLabel(content, text="", text_color=COLORS["accent"])

        self.btn_launch = ctk.CTkButton(content, text="Taramayı Başlat", height=50, font=("Roboto", 16, "bold"), 
                                        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"],
                                        command=self.start_scan)
        self.btn_launch.pack(fill="x", pady=20)

    def start_scan(self):
        domain = self.entry_domain.get()
        key = self.entry_key.get()
        if not domain or not key: return messagebox.showwarning("Hata", "Alanları doldurun.")
            
        # UI Kilitleme ve Progress Başlatma
        self.btn_launch.configure(state="disabled", text="Tarama Yapılıyor...")
        self.entry_domain.configure(state="disabled")
        self.entry_key.configure(state="disabled")
        
        self.progress_bar.pack(fill="x", pady=(10, 5)) # Göster
        self.lbl_status.pack(pady=5)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()
        self.lbl_status.configure(text="Sistemler başlatılıyor, modüller yükleniyor...")
        
        scan_data = {"domain": domain, "gemini_key": key, "user_id": self.current_user['id'], "internal_ip": None, "apk_path": None}
        scan_id = database.create_scan(scan_data, user_id=self.current_user['id'])
        
        threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data), daemon=True).start()

    def run_scan_logic(self, scan_id, data):
        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            img = "pentest-araci-kali:v1.5"
            dom = data['domain']
            
            # Paralel İşlemler
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fs = [
                    ex.submit(recon_module.run_reconnaissance, dom, dom, img, out),
                    ex.submit(web_app_module.run_web_tests, dom, img, out)
                ]
                # API Scan'i de ekleyelim
                # fs.append(ex.submit(api_module.run_api_tests, dom, img, out))
                for f in concurrent.futures.as_completed(fs): pass

            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            if path: database.complete_scan(scan_id, path, "COMPLETED")
            else: database.complete_scan(scan_id, None, "FAILED")
            
        except Exception as e:
            logging.error(e)
            database.complete_scan(scan_id, None, "FAILED")
        finally:
            # UI Sıfırlama (Main thread'e after ile gönderilmeli ideal olarak ama burası da çalışır)
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
    # RAPORLAR (Çalışan Arama ve Silme)
    # ==================================================================
    def create_reports_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Reports"] = view

        filter_bar = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], height=60, corner_radius=10)
        filter_bar.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(filter_bar, text="Arşiv Filtrele:", text_color=COLORS["text_gray"]).pack(side="left", padx=20)
        self.entry_search_reports = ctk.CTkEntry(filter_bar, placeholder_text="Domain ara...", width=300, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.entry_search_reports.pack(side="left", padx=10)
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
    # AYARLAR (Güvenli Kayıt)
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
        messagebox.showinfo("Başarılı", "Ayarlar kullanıcı dizinine güvenle kaydedildi.")

    # ==================================================================
    # DETAYLI RAPOR (Hata Yönetimi Eklendi)
    # ==================================================================
    def show_report_view(self, scan_id):
        if "ReportView" in self.frames: self.frames["ReportView"].destroy()
        
        scan = database.get_scan_by_id(scan_id)
        report_data = {}
        path = scan['report_file_path']
        if path and path.endswith(".html"): path = path.replace(".html", ".json")
        
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: report_data = json.load(f)
            except: pass

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
            ctk.CTkLabel(view, text="Rapor dosyası okunamadı veya bozuk.", text_color=COLORS["danger"]).pack(pady=50)

        self.show_view("ReportView")

    def create_report_card(self, parent, analiz):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=10)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=15)
        
        risk = analiz.get("risk_seviyesi", "").upper()
        col = COLORS["success"]
        if "KRITIK" in risk or "YÜKSEK" in risk or "HATA" in risk: col = COLORS["danger"]
        elif "ORTA" in risk: col = COLORS["warning"]

        ctk.CTkLabel(head, text=analiz.get("arac_adi"), font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
        ctk.CTkLabel(head, text=risk, text_color="white", fg_color=col, corner_radius=6, padx=8).pack(side="right")
        
        # Özet metni (Hata mesajları uzun olabilir, kırpma veya sarma yapalım)
        ozet = analiz.get("ozet", "Veri yok")
        if "Quota exceeded" in ozet: ozet = "⚠️ Google API Kotası aşıldı. Lütfen daha sonra tekrar deneyin veya API anahtarınızı kontrol edin."
        
        ctk.CTkLabel(card, text=ozet, font=("Roboto", 13), text_color="white", wraplength=900, justify="left").pack(fill="x", padx=20, pady=(0, 15))

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
        d = scan['created_at']
        if isinstance(d, str): d = d[:16] # String ise kırp
        elif isinstance(d, datetime.datetime): d = d.strftime("%Y-%m-%d %H:%M") # Objeyse formatla
        
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