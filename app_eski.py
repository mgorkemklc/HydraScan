import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import datetime
import threading
import json
import concurrent.futures
import logging
import glob
import subprocess
import queue  # EKLENDİ: Canlı log için
import requests # EKLENDİ: Bildirim için
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- MODÜLLER ---
import database
from core import recon_module, web_app_module, api_module, internal_network_module, report_module, mobile_module
from core.docker_helper import build_docker_image_stream

# --- CONFIG & LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USER_HOME = os.path.expanduser("~")
APP_DIR = os.path.join(USER_HOME, ".hydrascan")
if not os.path.exists(APP_DIR):
    os.makedirs(APP_DIR)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")

# --- RENKLER ---
# --- YENİ RENK PALETİ (Görseldeki Modern Dark Tema) ---
COLORS = {
    "bg_main": "#0b0f19",         # En arka plan (Çok koyu lacivert/siyah)
    "bg_panel": "#111827",        # Kartlar ve Yan Menü (Koyu gri/mavi)
    "bg_input": "#1f2937",        # Girdi alanları
    "accent": "#6366f1",          # Ana vurgu rengi (Neon Mor/İndigo)
    "accent_hover": "#4f46e5",    # Mor hover
    "text_white": "#f9fafb",      # Tam beyaz yerine yumuşak beyaz
    "text_gray": "#9ca3af",       # Soluk metinler
    "danger": "#f43f5e",          # Kırmızı (Neon)
    "success": "#10b981",         # Yeşil (Neon)
    "warning": "#f59e0b",         # Turuncu
    "running": "#3b82f6",         # Mavi
    "border": "#1f2937",          # İnce kenarlıklar
    "log_bg": "#030712",          # Terminal arkaplanı
    "terminal_fg": "#22d3ee"      # Terminal yazısı (Cyan)
}

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- YARDIMCI SINIFLAR ---
class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, sub_text, icon, icon_color):
        # Köşe ovalliğini artırdık (corner_radius=15)
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=15, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(1, weight=1)

        # Sol taraf: Metinler (Daha iyi hizalama için ayrı bir frame)
        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="w", padx=20, pady=20)

        ctk.CTkLabel(text_frame, text=title, font=("Roboto", 14), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.lbl_value = ctk.CTkLabel(text_frame, text=value, font=("Roboto", 36, "bold"), text_color="white")
        self.lbl_value.pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(text_frame, text=sub_text, font=("Roboto", 12), text_color=icon_color).pack(anchor="w")

        # Sağ taraf: İkon (Görseldeki gibi yuvarlak ve gölgeli/renkli arkaplan)
        self.icon_frame = ctk.CTkFrame(self, width=54, height=54, corner_radius=27, fg_color=COLORS["bg_input"])
        self.icon_frame.grid(row=0, column=2, padx=20, pady=20, sticky="e")
        self.icon_frame.pack_propagate(False) # İkon kutusunun boyutunu sabit tut
        ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 24), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

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

    def filter_cards_by_risk(self, risk_filter):
        """Seçilen risk grubuna göre kartları filtreler."""
        # Kart alanını temizle
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        ctk.CTkLabel(self.cards_container, text=f"Filtrelendi: {risk_filter}", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", pady=(10, 10))
        
        # "Tümünü Göster" butonu ekle
        ctk.CTkButton(self.cards_container, text="Filtreyi Temizle", height=24, width=100, 
                     fg_color=COLORS["bg_input"], command=lambda: self.sort_and_render_cards("risk_desc")).pack(anchor="w", padx=0, pady=(0, 10))

        count = 0
        for analiz in self.current_report_analizler:
            risk = analiz.get("risk_seviyesi", "Bilgilendirici").upper()
            target = risk_filter.upper()
            
            # Eşleşme kontrolü (Kritik -> KRITIK gibi)
            match = False
            if target == "KRITIK" and ("KRITIK" in risk or "CRITICAL" in risk): match = True
            elif target == "YÜKSEK" and ("YÜKSEK" in risk or "HIGH" in risk): match = True
            elif target == "ORTA" and ("ORTA" in risk or "MEDIUM" in risk): match = True
            elif target == "DÜŞÜK" and ("DÜŞÜK" in risk or "LOW" in risk): match = True
            elif target == "HATA" and ("HATA" in risk or "ERROR" in risk): match = True
            elif target == "BILGILENDIRICI" and match == False: match = True # Else durumu
            
            if match:
                self.create_report_card(self.cards_container, analiz, self.current_view_scan_id)
                count += 1
                
        if count == 0:
             ctk.CTkLabel(self.cards_container, text="Bu kategoride detay bulunamadı.", text_color="gray").pack()
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform")
        self.geometry("1400x900")
        self.configure(fg_color=COLORS["bg_main"])
        
        database.init_db()
        self.load_config()
        self.apply_theme() # EKLENDİ: Tema ayarını uygula
        self.current_user = None
        
        self.log_queue = queue.Queue() # EKLENDİ: Log kuyruğu
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.show_login_screen()

        self.check_log_queue() # EKLENDİ: Logları dinle

    def load_config(self):
        self.config = {"api_key": "", "theme": "Dark", "webhook_url": ""} # EKLENDİ: Webhook
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except: pass

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f)

    def apply_theme(self): # EKLENDİ
        ctk.set_appearance_mode(self.config.get("theme", "Dark"))

    def check_log_queue(self): # EKLENDİ: Terminal güncelleme
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if hasattr(self, 'terminal_box'):
                    self.terminal_box.configure(state="normal")
                    self.terminal_box.insert("end", msg)
                    self.terminal_box.see("end")
                    self.terminal_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.check_log_queue)

    # ==================================================================
    # LOGIN & REGISTER (AYNEN KORUNDU)
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
    # SYNC (AYNEN KORUNDU)
    # ==================================================================
    def sync_filesystem_to_db(self):
        if not os.path.exists("scan_outputs"): return
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

    def init_main_interface(self):
        for w in self.container.winfo_children(): w.destroy()
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        
        # Güncel Rolü Al
        self.user_role = self.current_user.get('role', 'Musteri')
        
        self.create_sidebar()
        
        self.main_area = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.create_header()
        
        self.frames = {}
        self.create_dashboard_view()
        self.create_reports_view()
        
        # YETKİ KONTROLÜ: Sadece Yetkili Roller Tarama ve Ayar Yapabilir
        if self.user_role in ["Superadmin", "Admin", "Pentester"]:
            self.create_web_scan_view()
            self.create_network_scan_view()
            self.create_mobile_scan_view()
            self.create_settings_view()
            
        # YETKİ KONTROLÜ: Sadece Superadmin Kullanıcı Yönetebilir
        if self.user_role == "Superadmin":
            self.create_user_management_view()

        self.show_view("Dashboard")

    def create_sidebar(self):
        sidebar = ctk.CTkFrame(self.container, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1)
        ctk.CTkLabel(sidebar, text="🐉 HYDRASCAN", font=("Roboto", 22, "bold"), text_color="white").pack(pady=30, padx=20, anchor="w")
        
        self.nav_btns = {}
        self.add_nav_btn(sidebar, "Genel Bakış", "📊", "Dashboard")
        
        # Sadece Yetkililere Gözüken Menüler
        if self.user_role in ["Superadmin", "Admin", "Pentester"]:
            ctk.CTkLabel(sidebar, text="TARAMA MODÜLLERİ", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
            self.add_nav_btn(sidebar, "Web Uygulama", "🌐", "WebScan")
            self.add_nav_btn(sidebar, "İç Ağ (Network)", "🖥️", "NetworkScan")
            self.add_nav_btn(sidebar, "Mobil Uygulama", "📱", "MobileScan")
        
        ctk.CTkLabel(sidebar, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
        self.add_nav_btn(sidebar, "Raporlar & Loglar", "📄", "Reports")
        
        if self.user_role in ["Superadmin", "Admin", "Pentester"]:
            self.add_nav_btn(sidebar, "Ayarlar", "⚙️", "Settings")
            
        if self.user_role == "Superadmin":
            self.add_nav_btn(sidebar, "Kullanıcılar", "👥", "Users")

        profile = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        initials = self.current_user['username'][:2].upper()
        ctk.CTkLabel(profile, text=initials, width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=10)
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        
        # Rolü de profil kısmında gösterelim
        ctk.CTkLabel(info, text=self.current_user['username'], font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text=self.user_role, font=("Roboto", 10), text_color=COLORS["text_gray"]).pack(anchor="w")
        
        ctk.CTkButton(profile, text="🚪", width=30, fg_color="transparent", text_color=COLORS["danger"], font=("Arial", 16), command=self.logout).pack(side="right", padx=10)

    def show_view(self, name):
        for frame in self.frames.values(): frame.grid_forget()
        if name in self.frames:
            self.frames[name].grid(row=1, column=0, sticky="nsew")
            
        titles = {
            "Dashboard": "Genel Bakış", "WebScan": "Web Uygulama Taraması", 
            "NetworkScan": "İç Ağ (Network) Taraması", "MobileScan": "Mobil Uygulama Taraması", 
            "Reports": "Rapor Arşivi", "Settings": "Ayarlar", "ReportView": "Detaylı Rapor",
            "Users": "Kullanıcı Yönetimi"
        }
        self.page_title.configure(text=titles.get(name, name))
        
        if name == "Dashboard": self.refresh_dashboard()
        if name == "Reports": self.refresh_reports_list()
        if name == "Users": self.refresh_users_list()
        
        for n, b in self.nav_btns.items():
            b.configure(fg_color=COLORS["bg_main"] if n == name else "transparent", text_color=COLORS["accent"] if n == name else COLORS["text_gray"])


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


    # ==================================================================
    # DASHBOARD (GÜNCELLENDİ: PROGRESS BAR EKLENDİ)
    # ==================================================================
    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Dashboard"] = view
        cards = ctk.CTkFrame(view, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 20))
        
        self.card_total = MetricCard(cards, "Toplam Tarama", "0", "Arşivde", "🗃️", COLORS["accent"])
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.card_active = MetricCard(cards, "Aktif Görevler", "0", "Şu an çalışıyor", "⏳", COLORS["warning"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=10)
        self.card_risk = MetricCard(cards, "Başarısız/Risk", "0", "İncelenmeli", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # --- YENİ EKLENEN PROGRESS BAR ALANI ---
        self.progress_frame = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=10)
        # Başlangıçta gizli duracak, tarama başlayınca ekrana getireceğiz
        
        self.lbl_status = ctk.CTkLabel(self.progress_frame, text="Sistem hazırlanıyor... (%0)", font=("Roboto", 14, "bold"), text_color="white")
        self.lbl_status.pack(pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=15, progress_color=COLORS["running"])
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 15))
        self.progress_bar.set(0)
        # --------------------------------------
        
        # CANLI TERMİNAL PENCERESİ
        term_frame = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=10)
        term_frame.pack(fill="x", padx=0, pady=(0, 20))

        action_frame = ctk.CTkFrame(view, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 10))
    
        ctk.CTkButton(action_frame, text="⛔ Seçili/Aktif Taramayı İptal Et", 
                  fg_color=COLORS["danger"], hover_color="#b91c1c", 
                  command=self.cancel_scan_action).pack(side="right", padx=10)
        
        term_head = ctk.CTkFrame(term_frame, fg_color="transparent")
        term_head.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(term_head, text=">_ CANLI TERMINAL", font=("Consolas", 12, "bold"), text_color=COLORS["success"]).pack(side="left")
        ctk.CTkButton(term_head, text="Temizle", width=60, height=20, command=lambda: self.terminal_box.delete("0.0", "end")).pack(side="right")
        
        self.terminal_box = ctk.CTkTextbox(term_frame, height=150, fg_color=COLORS["log_bg"], text_color=COLORS["terminal_fg"], font=("Consolas", 11))
        self.terminal_box.pack(fill="x", padx=5, pady=5)
        self.terminal_box.insert("0.0", "[*] Sistem hazır. Tarama bekleniyor...\n")
        
        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        cont.pack(fill="both", expand=True)
        self.tree = self.create_treeview(cont)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        self.tree.bind("<Double-1>", self.on_dashboard_click)

    def refresh_dashboard(self):
        # user_id yerine doğrudan self.current_user objesini gönderiyoruz
        scans = database.get_all_scans(self.current_user) 
        
        self.card_total.lbl_value.configure(text=str(len(scans)))
        self.card_active.lbl_value.configure(text=str(sum(1 for s in scans if s['status'] in ["RUNNING", "REPORTING"])))
        self.card_risk.lbl_value.configure(text=str(sum(1 for s in scans if s['status'] == "FAILED")))
        for i in self.tree.get_children(): self.tree.delete(i)
        for s in scans[:10]: self.insert_scan_to_tree(self.tree, s)

    def cancel_scan_action(self):
        sel = self.tree.selection()
        if not sel:
            # self.current_user['id'] yerine self.current_user gönderildi
            running_scans = [s for s in database.get_all_scans(self.current_user) if s['status'] == 'RUNNING']
            if running_scans:
                scan_id = running_scans[0]['id']
            else:
                return messagebox.showwarning("Uyarı", "İptal edilecek aktif bir tarama seçmediniz veya çalışan tarama yok.")
        else:
            scan_id = int(self.tree.item(sel[0])['values'][0])

        scan = database.get_scan_by_id(scan_id)
        if scan['status'] not in ['RUNNING', 'PENDING', 'REPORTING']:
            return messagebox.showinfo("Bilgi", "Bu tarama zaten tamamlanmış veya iptal edilmiş.")

        if not messagebox.askyesno("İptal", f"Tarama ID {scan_id} iptal edilsin mi?\n(Not: Arka plandaki işlemler durdurulamayabilir, ancak durum 'İPTAL' olarak işaretlenecek.)"):
            return

        database.update_scan_status(scan_id, "CANCELLED")
        self.refresh_dashboard()
        messagebox.showinfo("İptal Edildi", "Tarama durumu 'İptal Edildi' olarak güncellendi.")
        
    # ==================================================================
    # 🌐 WEB UYGULAMA MODÜLÜ
    # ==================================================================
    def create_web_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["WebScan"] = view
        scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Hedef
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text="Web Hedefi (Domain veya URL)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        self.entry_web_domain = ctk.CTkEntry(info_frame, placeholder_text="örn: example.com", height=45, fg_color=COLORS["bg_input"], border_color=COLORS["border"])
        self.entry_web_domain.pack(fill="x", padx=20, pady=(0, 20))
        
        # Wordlist
        wl_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        wl_frame.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(wl_frame, text="Özel Wordlist (Gobuster):", text_color="gray").pack(side="left")
        self.lbl_wordlist_path = ctk.CTkLabel(wl_frame, text="Varsayılan", text_color="white", font=("Roboto", 12, "italic"))
        self.lbl_wordlist_path.pack(side="left", padx=10)
        ctk.CTkButton(wl_frame, text="Dosya Seç", width=80, height=25, command=self.select_wordlist).pack(side="right")
        self.selected_wordlist_path = None

        # 2. Araçlar
        tools_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Web Tarama Araçları", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.web_tools_vars = {
            "whois": ctk.BooleanVar(value=True), "dig": ctk.BooleanVar(value=True), "subfinder": ctk.BooleanVar(value=True),
            "amass": ctk.BooleanVar(value=False), "nuclei": ctk.BooleanVar(value=True), "gobuster": ctk.BooleanVar(value=True),
            "sqlmap": ctk.BooleanVar(value=False), "dalfox": ctk.BooleanVar(value=False), "commix": ctk.BooleanVar(value=False),
            "wapiti": ctk.BooleanVar(value=False)
        }
        grid_frm = ctk.CTkFrame(tools_frame, fg_color="transparent")
        grid_frm.pack(fill="x", padx=20, pady=10)
        r, c = 0, 0
        for tool, var in self.web_tools_vars.items():
            cb = ctk.CTkCheckBox(grid_frm, text=tool.title(), variable=var, text_color="white", fg_color=COLORS["accent"])
            cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
            c += 1
            if c > 3: c=0; r+=1

        self.btn_web_launch = ctk.CTkButton(scroll, text="WEB TARAMASINI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=lambda: self.start_specific_scan("web"))
        self.btn_web_launch.pack(fill="x", pady=20)


    # ==================================================================
    # 🖥️ İÇ AĞ (NETWORK) MODÜLÜ
    # ==================================================================
    def create_network_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["NetworkScan"] = view
        scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text="Ağ Hedefi (IP veya CIDR)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        self.entry_net_ip = ctk.CTkEntry(info_frame, placeholder_text="örn: 192.168.1.0/24 veya 10.0.0.5", height=45, fg_color=COLORS["bg_input"], border_color=COLORS["border"])
        self.entry_net_ip.pack(fill="x", padx=20, pady=(0, 20))
        
        tools_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Ağ Tarama Araçları", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.net_tools_vars = {
            "nmap": ctk.BooleanVar(value=True), "hydra": ctk.BooleanVar(value=False)
        }
        grid_frm = ctk.CTkFrame(tools_frame, fg_color="transparent")
        grid_frm.pack(fill="x", padx=20, pady=10)
        r, c = 0, 0
        for tool, var in self.net_tools_vars.items():
            cb = ctk.CTkCheckBox(grid_frm, text=tool.title(), variable=var, text_color="white", fg_color=COLORS["accent"])
            cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
            c += 1
            if c > 3: c=0; r+=1

        self.btn_net_launch = ctk.CTkButton(scroll, text="AĞ TARAMASINI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=lambda: self.start_specific_scan("network"))
        self.btn_net_launch.pack(fill="x", pady=20)


    # ==================================================================
    # 📱 MOBİL UYGULAMA MODÜLÜ
    # ==================================================================
    def create_mobile_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["MobileScan"] = view
        scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        mobile_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        mobile_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(mobile_frame, text="Mobil Uygulama Dosyası", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.apk_input_frame = ctk.CTkFrame(mobile_frame, fg_color="transparent")
        self.apk_input_frame.pack(fill="x", padx=20, pady=(0, 20))
        self.lbl_apk_path = ctk.CTkLabel(self.apk_input_frame, text="Dosya seçilmedi", text_color=COLORS["text_gray"])
        self.lbl_apk_path.pack(side="left", padx=10)
        ctk.CTkButton(self.apk_input_frame, text="Dosya Yükle", width=100, command=self.select_apk, fg_color=COLORS["bg_input"]).pack(side="left")
        self.selected_apk_path = None

        self.btn_mob_launch = ctk.CTkButton(scroll, text="MOBİL TARAMAYI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=lambda: self.start_specific_scan("mobile"))
        self.btn_mob_launch.pack(fill="x", pady=20)

    def select_wordlist(self): # EKLENDİ
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if path:
            self.selected_wordlist_path = path
            self.lbl_wordlist_path.configure(text=os.path.basename(path), text_color="white")

    def toggle_apk_input(self):
        if self.tools_vars["mobile"].get(): self.apk_input_frame.pack(fill="x", padx=40, pady=(0, 20))
        else: self.apk_input_frame.pack_forget()

    def select_apk(self):
        path = filedialog.askopenfilename(filetypes=[("Android Package", "*.apk *.aab *.xapk")])
        if path:
            self.selected_apk_path = path
            self.lbl_apk_path.configure(text=os.path.basename(path), text_color="white")

    # --- TARAMA MANTIĞI (GÜNCELLENDİ: LOG CALLBACK VE WORDLIST İLE) ---
    def start_specific_scan(self, scan_type):
        domain = ""
        key = self.config.get("api_key", "")
        selected_tools = []
        apk_path = None
        wordlist_path = None

        if not key:
            return messagebox.showwarning("Eksik", "Ayarlar sayfasından Gemini API Key girmelisiniz.")

        if scan_type == "web":
            domain = self.entry_web_domain.get()
            selected_tools = [k for k, v in self.web_tools_vars.items() if v.get()]
            wordlist_path = self.selected_wordlist_path
            if not domain: return messagebox.showwarning("Eksik", "Lütfen bir Web Hedefi (Domain) girin.")

        elif scan_type == "network":
            domain = self.entry_net_ip.get()
            selected_tools = [k for k, v in self.net_tools_vars.items() if v.get()]
            if not domain: return messagebox.showwarning("Eksik", "Lütfen bir Ağ Hedefi (IP) girin.")

        elif scan_type == "mobile":
            domain = "Mobil_Uygulama_Taramasi"
            selected_tools = ["mobile"]
            apk_path = self.selected_apk_path
            if not apk_path: return messagebox.showwarning("Eksik", "Lütfen bir APK dosyası seçin.")

        # İşlemi başlat ve terminale geçir
        self.terminal_box.configure(state="normal")
        self.terminal_box.delete("0.0", "end")
        self.terminal_box.configure(state="disabled")
        self.show_view("Dashboard")

        # Progress Bar'ı Dashboard'da Terminalin üzerine ekleyerek göster
        self.progress_frame.pack(fill="x", pady=(0, 20), before=self.terminal_box.master) 
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Tarama başlatılıyor... (%0)")

        scan_data = {
            "domain": domain, 
            "gemini_key": key, 
            "apk_path": apk_path,
            "wordlist": wordlist_path,
            "scan_type": scan_type
        }
        
        try:
            scan_id = database.create_scan(scan_data, user_id=self.current_user['id'])
            threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data, selected_tools), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def run_scan_logic(self, scan_id, data, selected_tools):
        # Log Callback Fonksiyonu
        def log_cb(msg): self.log_queue.put(msg)

        log_cb(f"[*] Tarama Başlatılıyor ID: {scan_id} (Modül: {data.get('scan_type', 'Bilinmiyor').upper()})\n")

        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            img = "pentest-araci-kali:v1.5"
            dom = data['domain']
            scan_type = data.get('scan_type')
            
            futures = []
            extracted_urls = []

            with concurrent.futures.ThreadPoolExecutor() as ex:
                if scan_type == "web":
                    futures.append(ex.submit(recon_module.run_reconnaissance, dom, out, img, selected_tools))
                    # Web modülünde custom_wordlist gönderiyoruz
                    futures.append(ex.submit(web_app_module.run_web_tests, dom, out, img, selected_tools, stream_callback=log_cb, custom_wordlist=data.get('wordlist')))
                
                elif scan_type == "network":
                    # İç ağ modülünü çağırıyoruz
                    futures.append(ex.submit(internal_network_module.run_network_tests, dom, out, img, selected_tools))
                
                elif scan_type == "mobile":
                    # Mobil modül çalışır ve geriye bulduğu backend linklerini (list) döndürür
                    future_mob = ex.submit(mobile_module.run_mobile_tests, data['apk_path'], out, img, stream_callback=log_cb)
                    futures.append(future_mob)

                total_steps = len(futures) + 1
                completed_steps = 0
                
                for f in concurrent.futures.as_completed(futures):
                    # Eğer çalışan şey Mobil modülse ve sonuç döndürdüyse URL'leri yakala
                    if scan_type == "mobile" and f == futures[0]:
                        try:
                            result = f.result()
                            if isinstance(result, list):
                                extracted_urls.extend(result)
                        except Exception as e:
                            log_cb(f"[-] Mobil modül URL çıkarma hatası: {e}\n")

                    completed_steps += 1
                    progress_val = completed_steps / total_steps
                    self.after(0, self.update_progress_ui, progress_val, f"Taramalar tamamlanıyor... (%{int(progress_val*100)})")

            self.after(0, self.update_progress_ui, 0.9, "AI Raporu hazırlanıyor... (%90)")
            log_cb("[*] AI Raporu hazırlanıyor...\n")
            
            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            status = "COMPLETED" if path else "FAILED"
            database.complete_scan(scan_id, path, status)
            
            # webhook bildirim
            if hasattr(self, 'send_notification'):
                self.send_notification(dom, status)
                
            log_cb(f"[+] Tarama Tamamlandı. Durum: {status}\n")

            self.after(0, self.update_progress_ui, 1.0, "Tamamlandı! (%100)")
            self.after(1000, self.reset_scan_ui)

            # =========================================================
            # ZİNCİRLEME SALDIRI (API ROUTING) TETİKLEYİCİSİ
            # =========================================================
            if extracted_urls:
                # Thread bittikten 1.5 saniye sonra kullanıcıya sor
                self.after(1500, self.prompt_chained_attack, extracted_urls)

        except Exception as e:
            import traceback
            traceback.print_exc()
            log_cb(f"[-] Kritik Hata: {e}\n")
            database.complete_scan(scan_id, None, "FAILED")
            self.after(0, self.reset_scan_ui)

    def prompt_chained_attack(self, urls):
        """Mobil analizden dönen URL'leri Web/API modülüne aktarmak için onay ister."""
        # Gösterilecek linkleri hazırla
        url_list_str = "\n".join(urls[:5])
        if len(urls) > 5:
            url_list_str += f"\n... ve {len(urls)-5} tane daha."
            
        msg = f"Mobil uygulamanın kaynak kodunda {len(urls)} adet Backend API / Web URL'si tespit edildi:\n\n{url_list_str}\n\nBu hedeflere otomatik olarak Web/API Sızma Testi (Zincirleme Saldırı) başlatmak ister misiniz?"
        
        if messagebox.askyesno("🔗 Zincirleme Saldırı", msg):
            self.show_view("WebScan")
            self.entry_web_domain.delete(0, "end")
            
            # İlk URL'yi temizle (http:// çıkarma vb. işlemleri)
            target_url = urls[0] 
            from urllib.parse import urlparse
            parsed = urlparse(target_url)
            clean_domain = parsed.netloc if parsed.netloc else target_url
            
            self.entry_web_domain.insert(0, clean_domain)
            messagebox.showinfo("Hedef Aktarıldı", f"En belirgin Backend sunucusu olan '{clean_domain}' Web Tarama modülüne aktarıldı.\n\nGerekli araçları seçip 'Taramayı Başlat' butonuna basarak API testini başlatabilirsiniz.")


    def send_notification(self, domain, status): # EKLENDİ
        webhook = self.config.get("webhook_url")
        if webhook:
            try: requests.post(webhook, json={"content": f"📢 HydraScan: {domain} taraması bitti. Durum: {status}"})
            except: pass

    def update_progress_ui(self, val, text):
        self.progress_bar.set(val)
        self.lbl_status.configure(text=text)

    def reset_scan_ui(self):
        # Sadece Dashboard'daki progress bar'ı gizle
        if hasattr(self, 'progress_frame'):
            self.progress_frame.pack_forget()
        
        self.refresh_dashboard()
        messagebox.showinfo("Bilgi", "Tarama işlemi sonlandı.")

    # --- REPORTS & SETTINGS (GÜNCELLENDİ: PDF BUTONU EKLENDİ) ---
    def create_reports_view(self, parent=None): # parent parametresi opsiyonel
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
        
        # EKLENDİ: PDF BUTONU
        ctk.CTkButton(btn_frm, text="📄 PDF İndir", fg_color=COLORS["success"], command=self.download_pdf_action).pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frm, text="⚖️ Karşılaştır", fg_color=COLORS["warning"], text_color="black", 
                      command=self.on_compare_click).pack(side="left", padx=10)

        ctk.CTkButton(btn_frm, text="Seçili Taramayı Sil", fg_color=COLORS["danger"], hover_color="#dc2626", command=self.delete_selected_scan).pack(side="right")

    def download_pdf_action(self):
        sel = self.reports_tree.selection()
        if not sel: return messagebox.showwarning("Uyarı", "Lütfen bir rapor seçin.")
        
        # Seçili satırdan ID'yi al
        sid = int(self.reports_tree.item(sel[0])['values'][0])
        
        # Veritabanından veriyi çek
        scan = database.get_scan_by_id(sid)
        
        # HATA DÜZELTMESİ BURADA:
        # scan.get(...) yerine scan[...] kullanıyoruz çünkü sqlite3.Row objesi .get() desteklemez.
        try:
            json_path = scan['report_file_path']
        except:
            json_path = None
        
        if not json_path or not os.path.exists(json_path):
            return messagebox.showerror("Hata", "Rapor dosyası bulunamadı veya silinmiş.")
            
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Dosyası", "*.pdf")])
        if save_path:
            # report_module içindeki fonksiyonu çağır
            if report_module.export_to_pdf(json_path, save_path):
                messagebox.showinfo("Başarılı", "PDF başarıyla oluşturuldu.")
            else:
                messagebox.showerror("Hata", "PDF oluşturulurken bir hata oluştu.")

    def refresh_reports_list(self):
        self.sync_filesystem_to_db()
        search = self.entry_search_reports.get().lower()
        
        # user_id yerine doğrudan self.current_user objesini gönderiyoruz
        scans = database.get_all_scans(self.current_user)
        
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

    def create_risk_chart(self, parent_frame, report_data):
        # 1. Verileri Say
        risk_counts = {"Kritik": 0, "Yüksek": 0, "Orta": 0, "Düşük": 0, "Bilgilendirici": 0, "Hata": 0}
        for analiz in report_data.get("analizler", []):
            risk = analiz.get("risk_seviyesi", "Bilgilendirici")
            risk_upper = risk.upper()
            if "KRITIK" in risk_upper or "CRITICAL" in risk_upper: risk_counts["Kritik"] += 1
            elif "YÜKSEK" in risk_upper or "HIGH" in risk_upper: risk_counts["Yüksek"] += 1
            elif "ORTA" in risk_upper or "MEDIUM" in risk_upper: risk_counts["Orta"] += 1
            elif "DÜŞÜK" in risk_upper or "LOW" in risk_upper: risk_counts["Düşük"] += 1
            elif "HATA" in risk_upper or "ERROR" in risk_upper: risk_counts["Hata"] += 1
            else: risk_counts["Bilgilendirici"] += 1

        labels = [k for k, v in risk_counts.items() if v > 0]
        sizes = [v for k, v in risk_counts.items() if v > 0]
        
        colors_map = {
            "Kritik": "#ef4444", "Yüksek": "#f97316", "Orta": "#eab308",
            "Düşük": "#3b82f6", "Bilgilendirici": "#94a3b8", "Hata": "#64748b"
        }
        colors = [colors_map.get(l, "#94a3b8") for l in labels]

        if not sizes: return

        # 2. Grafik Oluştur
        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        fig.patch.set_facecolor(COLORS["bg_panel"])
        ax.set_facecolor(COLORS["bg_panel"])

        # 'picker=True' ekleyerek tıklanabilir yapıyoruz
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.1f%%',
            startangle=90, pctdistance=0.85, textprops=dict(color="white"),
            wedgeprops={'picker': True} # TIKLANABİLİR YAPMA AYARI
        )

        centre_circle = plt.Circle((0,0), 0.70, fc=COLORS["bg_panel"])
        fig.gca().add_artist(centre_circle)
        ax.axis('equal')
        plt.title("Risk Dağılımı (Filtrelemek için Tıkla)", color="white", fontsize=10, pad=10)

        # 3. Canvas ve Tıklama Olayı (Event)
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=10)

        # Tıklama fonksiyonu
        def on_pick(event):
            wedge = event.artist
            # Hangi dilime tıklandığını bul
            label_index = wedges.index(wedge)
            selected_label = labels[label_index]
            
            # Filtreleme fonksiyonunu çağır
            self.filter_cards_by_risk(selected_label)

        # Olayı bağla
        fig.canvas.mpl_connect('pick_event', on_pick)

    def on_compare_click(self):
        # 1. Seçili satırları al
        selection = self.reports_tree.selection()
        
        if len(selection) != 2:
            return messagebox.showwarning("Uyarı", "Karşılaştırma yapmak için listeden tam olarak 2 rapor seçmelisiniz.\n(CTRL tuşuna basılı tutarak seçim yapabilirsiniz)")
        
        # ID'leri al
        id1 = int(self.reports_tree.item(selection[0])['values'][0])
        id2 = int(self.reports_tree.item(selection[1])['values'][0])
        
        # Karşılaştırma ekranını aç
        self.show_compare_view(id1, id2)

    def show_compare_view(self, id1, id2):
        # 1. Ekranı temizle
        if "CompareView" in self.frames: self.frames["CompareView"].destroy()
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["CompareView"] = view
        
        # 2. Verileri Çek
        scan_a = database.get_scan_by_id(id1)
        scan_b = database.get_scan_by_id(id2)
        
        # --- HATA DÜZELTMESİ: sqlite3.Row Nesnesinden Veri Okuma ---
        try:
            date_a = scan_a['created_at']
        except: date_a = ""
        
        try:
            date_b = scan_b['created_at']
        except: date_b = ""
        
        # Tarihe göre sırala (Eskisi -> old, Yenisi -> new)
        if str(date_a) < str(date_b):
            old_scan, new_scan = scan_a, scan_b
        else:
            old_scan, new_scan = scan_b, scan_a

        # 3. Üst Bar (Geri Butonu ve Başlık)
        top_bar = ctk.CTkFrame(view, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(top_bar, text="← Geri", width=80, fg_color=COLORS["bg_panel"], command=lambda: self.show_view("Reports")).pack(side="left")
        
        title_text = f"Karşılaştırma: {old_scan['id']} (Eski) vs {new_scan['id']} (Yeni)"
        ctk.CTkLabel(top_bar, text=title_text, font=("Roboto", 18, "bold"), text_color="white").pack(side="left", padx=20)

        # 4. JSON Verilerini Yükle ve Ayrıştır (İç Fonksiyon)
        def load_findings(scan):
            findings_set = set() # (Araç, Bulgu Özeti)
            try:
                # sqlite3.Row hatası olmaması için doğrudan erişim
                path = scan['report_file_path']
                
                if path and path.endswith(".html"): path = path.replace(".html", ".json")
                if path and os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        for analiz in data.get("analizler", []):
                            tool = analiz.get("arac_adi", "Unknown")
                            for b in analiz.get("bulgular", []):
                                # Bulguyu temizle ve sete ekle
                                clean_b = str(b).strip()[:200] 
                                findings_set.add((tool, clean_b))
            except Exception as e:
                print(f"Veri yükleme hatası: {e}")
            return findings_set

        # Bulguları yükle
        old_findings = load_findings(old_scan)
        new_findings = load_findings(new_scan)

        # 5. Kümeler Teorisi (Farkları Bul)
        fixed_issues = old_findings - new_findings # Eskide var, yenide yok (Giderilmiş)
        new_issues = new_findings - old_findings   # Yenide var, eskide yok (Yeni Risk)
        same_issues = old_findings & new_findings  # İkisinde de var (Devam Ediyor)

        # 6. Görselleştirme Alanı (Grid)
        grid_frame = ctk.CTkFrame(view, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.grid_columnconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(1, weight=1)
        grid_frame.grid_columnconfigure(2, weight=1)
        grid_frame.grid_rowconfigure(0, weight=1)

        # Helper Fonksiyon: Sütun Oluşturucu (ÖNCE TANIMLANIYOR)
        def create_column(col_idx, title, color, items, icon):
            frm = ctk.CTkFrame(grid_frame, fg_color=COLORS["bg_panel"], corner_radius=10)
            frm.grid(row=0, column=col_idx, sticky="nsew", padx=5, pady=5)
            
            header = ctk.CTkFrame(frm, fg_color=color, height=40, corner_radius=10)
            header.pack(fill="x", padx=2, pady=2)
            ctk.CTkLabel(header, text=f"{icon} {title} ({len(items)})", font=("Roboto", 14, "bold"), text_color="white").pack(pady=5)
            
            scroll = ctk.CTkScrollableFrame(frm, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=5, pady=5)
            
            if not items:
                ctk.CTkLabel(scroll, text="Veri yok", text_color="gray").pack(pady=20)
            
            for tool, finding in items:
                card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_main"], border_width=0, corner_radius=6)
                card.pack(fill="x", pady=2)
                ctk.CTkLabel(card, text=tool, font=("Roboto", 10, "bold"), text_color=color).pack(anchor="w", padx=5, pady=(2,0))
                ctk.CTkLabel(card, text=finding, font=("Roboto", 11), text_color="white", wraplength=300).pack(anchor="w", padx=5, pady=(0,2))

        # 7. Sütunları Oluştur (ŞİMDİ ÇAĞRILIYOR)
        # 1. Sütun: GİDERİLENLER (Yeşil)
        create_column(0, "Giderilenler", COLORS["success"], list(fixed_issues), "🎉")

        # 2. Sütun: YENİ BULGULAR (Kırmızı)
        create_column(1, "Yeni Bulgular", COLORS["danger"], list(new_issues), "🚨")

        # 3. Sütun: DEVAM EDENLER (Turuncu/Gri)
        create_column(2, "Devam Edenler", COLORS["warning"], list(same_issues), "⚠️")

        # 8. Görünümü Aktif Et
        self.show_view("CompareView")

    def create_settings_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Settings"] = view
        cont = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        cont.pack(fill="both", expand=True, padx=50, pady=20)
        ctk.CTkLabel(cont, text="Uygulama Ayarları", font=("Roboto", 20, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(40, 20))
        
        # API Key
        ctk.CTkLabel(cont, text="Varsayılan Gemini API Anahtarı", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(10, 5))
        self.set_api = ctk.CTkEntry(cont, placeholder_text="API Key...", width=500, height=45, fg_color=COLORS["bg_main"], border_color=COLORS["border"])
        self.set_api.pack(anchor="w", padx=40, pady=(0, 20))
        if "api_key" in self.config: self.set_api.insert(0, self.config["api_key"])
        
        # EKLENDİ: Webhook URL & Tema
        ctk.CTkLabel(cont, text="Bildirim Webhook (Discord/Slack)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(10, 5))
        self.set_webhook = ctk.CTkEntry(cont, width=500, height=45, fg_color=COLORS["bg_main"])
        self.set_webhook.pack(anchor="w", padx=40, pady=5)
        if self.config.get("webhook_url"): self.set_webhook.insert(0, self.config["webhook_url"])
        
        ctk.CTkLabel(cont, text="Tema", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(15, 5))
        self.theme_switch = ctk.CTkSwitch(cont, text="Aydınlık Mod", command=self.toggle_theme)
        self.theme_switch.pack(anchor="w", padx=40)
        if self.config.get("theme") == "Light": self.theme_switch.select()

        ctk.CTkButton(cont, text="Ayarları Kaydet", width=200, height=45, fg_color=COLORS["success"], hover_color="#16a34a", command=self.save_settings).pack(anchor="w", padx=40, pady=(30, 40))
        
        # --- DOCKER UPDATE BUTONU (AYNEN KORUNDU) ---
        ctk.CTkLabel(cont, text="Sistem Bakımı", font=("Roboto", 20, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(20, 20))
        info_text = "Eğer araçlarda 'Command not found' veya 'Missing dependency' hatası alıyorsanız,\nbu butona basarak Pentest Araçlarını (Docker İmajını) yeniden yükleyin."
        ctk.CTkLabel(cont, text=info_text, font=("Roboto", 12), text_color=COLORS["text_gray"], justify="left").pack(anchor="w", padx=40, pady=(0, 15))
        self.btn_update_docker = ctk.CTkButton(cont, text="🛠️ Araçları Güncelle / Onar (Rebuild)", width=300, height=50, fg_color=COLORS["warning"], hover_color="#d97706", text_color="black", font=("Roboto", 14, "bold"), command=self.start_docker_update)
        self.btn_update_docker.pack(anchor="w", padx=40, pady=10)

    # ==================================================================
    # 👥 KULLANICI YÖNETİMİ (SUPERADMIN)
    # ==================================================================
    def create_user_management_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Users"] = view
        
        # 1. Yeni Kullanıcı Ekleme Formu
        form_frame = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=10)
        form_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(form_frame, text="Yeni Kullanıcı Tanımla", font=("Roboto", 16, "bold"), text_color="white").pack(anchor="w", padx=20, pady=(15, 10))
        
        inputs_frm = ctk.CTkFrame(form_frame, fg_color="transparent")
        inputs_frm.pack(fill="x", padx=20, pady=(0, 15))
        
        self.new_user_name = ctk.CTkEntry(inputs_frm, placeholder_text="Kullanıcı Adı")
        self.new_user_name.pack(side="left", padx=5)
        
        self.new_user_pass = ctk.CTkEntry(inputs_frm, placeholder_text="Şifre", show="*")
        self.new_user_pass.pack(side="left", padx=5)
        
        self.new_user_role = ctk.CTkOptionMenu(inputs_frm, values=["Musteri", "Pentester", "Admin", "Superadmin"])
        self.new_user_role.pack(side="left", padx=5)
        
        self.new_user_company = ctk.CTkEntry(inputs_frm, placeholder_text="Şirket ID (Örn: 1)", width=120)
        self.new_user_company.pack(side="left", padx=5)
        
        ctk.CTkButton(inputs_frm, text="Kullanıcıyı Ekle", fg_color=COLORS["success"], command=self.add_user_action).pack(side="left", padx=10)

        # 2. Kullanıcı Listesi (Treeview)
        list_frame = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=10)
        list_frame.pack(fill="both", expand=True)
        
        ctk.CTkButton(list_frame, text="Seçili Kullanıcıyı Sil", fg_color=COLORS["danger"], command=self.delete_user_action).pack(anchor="e", padx=20, pady=10)
        
        self.users_tree = ttk.Treeview(list_frame, columns=("ID", "Kullanici", "Rol", "Sirket"), show="headings")
        self.users_tree.heading("ID", text="ID")
        self.users_tree.column("ID", width=50, anchor="center")
        self.users_tree.heading("Kullanici", text="KULLANICI ADI")
        self.users_tree.heading("Rol", text="YETKİ ROLÜ")
        self.users_tree.heading("Sirket", text="BAĞLI ŞİRKET")
        self.users_tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def add_user_action(self):
        u, p, r, c = self.new_user_name.get(), self.new_user_pass.get(), self.new_user_role.get(), self.new_user_company.get()
        if not u or not p: return messagebox.showwarning("Hata", "Kullanıcı adı ve şifre zorunludur.")
        
        # Şirket ID'si girilmediyse varsayılan olarak 1 (Hydra Security) ata
        c_id = int(c) if c.isdigit() else 1 
        
        if database.register_user(u, p, role=r, company_id=c_id):
            messagebox.showinfo("Başarılı", f"{u} kullanıcısı ({r}) olarak eklendi.")
            self.refresh_users_list()
        else:
            messagebox.showerror("Hata", "Bu kullanıcı adı zaten mevcut.")

    def delete_user_action(self):
        sel = self.users_tree.selection()
        if not sel: return
        uid = int(self.users_tree.item(sel[0])['values'][0])
        
        if uid == self.current_user['id']:
            return messagebox.showwarning("Hata", "Kendi (aktif) hesabınızı silemezsiniz.")
            
        if messagebox.askyesno("Emin misiniz?", "Bu kullanıcıyı sistemden tamamen silmek istediğinize emin misiniz?"):
            database.delete_user(uid)
            self.refresh_users_list()

    def refresh_users_list(self):
        if not hasattr(self, 'users_tree'): return
        for i in self.users_tree.get_children(): self.users_tree.delete(i)
        
        for u in database.get_all_users():
            c_name = u['company_name'] if u['company_name'] else "Sistem / Bağımsız"
            self.users_tree.insert("", "end", values=(u['id'], u['username'], u['role'], c_name))

    def toggle_theme(self):
        # 1. Modu Belirle
        mode = "Light" if self.theme_switch.get() else "Dark"
        # 2. Görünümü Uygula
        ctk.set_appearance_mode(mode)
        # 3. Ayarı Belleğe Kaydet
        self.config["theme"] = mode
        # 4. Dosyaya Yaz (BU SATIR EKSİKTİ, EKLENDİ)
        self.save_config()
        
    def save_settings(self):
        self.config["api_key"] = self.set_api.get()
        self.config["webhook_url"] = self.set_webhook.get() # EKLENDİ
        self.save_config()
        messagebox.showinfo("Başarılı", "Ayarlar kaydedildi.")

    def start_docker_update(self):
        if not messagebox.askyesno("Onay", "Bu işlem Docker imajını sıfırdan oluşturacak. Devam mı?"): return
        self.btn_update_docker.configure(state="disabled", text="İşlem Başlatılıyor...")
        self.update_window = ctk.CTkToplevel(self)
        self.update_window.title("Sistem Güncellemesi")
        self.update_window.geometry("800x600")
        self.update_window.configure(fg_color=COLORS["bg_main"])
        self.update_window.attributes("-topmost", True)
        self.update_log_box = ctk.CTkTextbox(self.update_window, fg_color=COLORS["log_bg"], text_color="#00ff00", font=("Consolas", 11))
        self.update_log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.update_log_box.insert("0.0", "[*] Güncelleme başlatılıyor...\n")
        threading.Thread(target=self.run_docker_update, daemon=True).start()

    def run_docker_update(self):
        try:
            for line in build_docker_image_stream():
                self.update_log_box.insert("end", line)
                self.update_log_box.see("end")
            self.update_log_box.insert("end", "\n[+] İŞLEM BAŞARILI! ✅")
            messagebox.showinfo("Başarılı", "Docker imajı güncellendi!")
        except Exception as e:
            self.update_log_box.insert("end", f"\n[-] HATA: {str(e)}\n")
            messagebox.showerror("Hata", str(e))
        finally:
            self.btn_update_docker.configure(state="normal", text="🛠️ Araçları Güncelle / Onar (Rebuild)")

    # --- DETAY RAPOR (AYNEN KORUNDU) ---
    def show_report_view(self, scan_id):
        # 1. Mevcut ekranı temizle
        if "ReportView" in self.frames: self.frames["ReportView"].destroy()
        
        # 2. Veritabanından ve JSON dosyasından veriyi çek
        scan = database.get_scan_by_id(scan_id)
        self.current_view_scan_id = scan_id 
        
        report_data = {}
        path = scan['report_file_path']
        # HTML uzantısı varsa JSON'a çevirip oku
        if path and path.endswith(".html"): path = path.replace(".html", ".json")
        
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: report_data = json.load(f)
            except: pass
        
        # Analiz listesini sınıf değişkenine ata (Sıralama fonksiyonu kullanacak)
        self.current_report_analizler = report_data.get("analizler", [])

        # 3. Ana Görünüm Çerçevesini Oluştur
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["ReportView"] = view
        
        # --- Üst Bar (Geri Butonu ve Başlık) ---
        top_bar = ctk.CTkFrame(view, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(top_bar, text="← Geri", width=80, fg_color=COLORS["bg_panel"], command=lambda: self.show_view("Dashboard")).pack(side="left")
        ctk.CTkLabel(top_bar, text=f"Rapor: {scan['target_full_domain']}", font=("Roboto", 20, "bold"), text_color="white").pack(side="left", padx=20)

        if report_data:
            # --- ANA SCROLL ALANI (Tüm sayfa bunun içinde kayacak) ---
            self.report_main_scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
            self.report_main_scroll.pack(fill="both", expand=True)

            # A) GRAFİK ALANI (En üstte)
            stats_frame = ctk.CTkFrame(self.report_main_scroll, fg_color="transparent")
            stats_frame.pack(fill="x", pady=(0, 20))
            
            # Grafiği tutan kutu
            chart_frame = ctk.CTkFrame(stats_frame, fg_color=COLORS["bg_panel"], corner_radius=12)
            chart_frame.pack(side="left", padx=(0, 10))
            
            # Grafiği çizdir (Hata olursa program çökmesin diye try-except)
            try:
                self.create_risk_chart(chart_frame, report_data)
            except Exception as e:
                print(f"Grafik hatası: {e}")

            # B) SIRALAMA BUTONLARI (Grafiğin altında)
            sort_bar = ctk.CTkFrame(self.report_main_scroll, fg_color="transparent", height=40)
            sort_bar.pack(fill="x", pady=(0, 10), anchor="w")
            
            ctk.CTkLabel(sort_bar, text="Sıralama:", text_color=COLORS["text_gray"], font=("Roboto", 12)).pack(side="left", padx=(0, 10))
            
            ctk.CTkButton(sort_bar, text="🔥 Risk (Yüksek → Düşük)", 
                          height=28, fg_color=COLORS["bg_input"], hover_color=COLORS["bg_panel"],
                          command=lambda: self.sort_and_render_cards("risk_desc")).pack(side="left", padx=5)

            ctk.CTkButton(sort_bar, text="🔤 İsim (A-Z)", 
                          height=28, fg_color=COLORS["bg_input"], hover_color=COLORS["bg_panel"],
                          command=lambda: self.sort_and_render_cards("name")).pack(side="left", padx=5)

            # C) KARTLARIN BASILACAĞI ALAN (Boş bir kutu oluşturuyoruz)
            # Sıralama fonksiyonu SADECE BURAYI temizleyip dolduracak.
            self.cards_container = ctk.CTkFrame(self.report_main_scroll, fg_color="transparent")
            self.cards_container.pack(fill="both", expand=True)
            
            # İlk açılışta varsayılan sıralama ile doldur
            self.sort_and_render_cards("risk_desc")

        else:
            ctk.CTkLabel(view, text="Rapor verisi yok veya bozuk.", text_color=COLORS["danger"]).pack(pady=50)
            
        self.show_view("ReportView")

    def get_risk_score(self, risk_str):
        """Risk metnini sayısal puana çevirir (Sıralama için)."""
        risk_map = {
            "KRİTİK": 5, "CRITICAL": 5,
            "YÜKSEK": 4, "HIGH": 4, "YUKSEK": 4,
            "ORTA": 3, "MEDIUM": 3,
            "DÜŞÜK": 2, "LOW": 2,
            "BİLGİLENDİRİCİ": 1, "INFO": 1,
            "ARAÇ HATASI": 0, "HATA": 0
        }
        # Türkçe karakter sorunu olmaması için upper() kullanıyoruz
        return risk_map.get(risk_str.upper(), 0)
    
    def sort_and_render_cards(self, criteria):
        """Kartları belirtilen kritere göre sıralar ve cards_container içine basar."""
        
        # 1. Sadece kartların olduğu alanı temizle (Grafik ve butonlar kalır)
        for widget in self.cards_container.winfo_children():
            widget.destroy()
            
        # 2. Listeyi Hafızada Sırala
        if criteria == "risk_desc": # Risk: Büyükten Küçüğe
            self.current_report_analizler.sort(
                key=lambda x: self.get_risk_score(x.get("risk_seviyesi", "")), 
                reverse=True
            )
        elif criteria == "risk_asc": # Risk: Küçükten Büyüğe (İstersen ekleyebilirsin)
            self.current_report_analizler.sort(
                key=lambda x: self.get_risk_score(x.get("risk_seviyesi", ""))
            )
        elif criteria == "name": # İsim: A-Z
            self.current_report_analizler.sort(
                key=lambda x: x.get("arac_adi", "").lower()
            )

        # 3. Kartları Yeniden Oluştur
        ctk.CTkLabel(self.cards_container, text="Detaylı Analiz Sonuçları", font=("Roboto", 16, "bold"), text_color="white").pack(anchor="w", pady=(10, 10))
        
        for analiz in self.current_report_analizler:
            # create_report_card fonksiyonun zaten var, onu kullanıyoruz
            self.create_report_card(self.cards_container, analiz, self.current_view_scan_id)

    def create_report_card(self, parent, analiz, scan_id):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=10)
        
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(head, text=analiz.get("arac_adi"), font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
        
        right_box = ctk.CTkFrame(head, fg_color="transparent")
        right_box.pack(side="right")
        
        ctk.CTkButton(right_box, text="📜 Ham Çıktı", width=100, height=28, fg_color=COLORS["bg_input"], hover_color=COLORS["bg_main"], font=("Roboto", 11), command=lambda: self.view_raw_log(scan_id, analiz.get("arac_adi"))).pack(side="left", padx=5)

        risk = analiz.get("risk_seviyesi", "").upper()
        col = COLORS["success"]
        if "KRITIK" in risk or "YÜKSEK" in risk: col = COLORS["danger"]
        elif "ARAÇ HATASI" in risk or "HATA" in risk: col = COLORS["danger"]
        elif "ORTA" in risk: col = COLORS["warning"]
        
        ctk.CTkLabel(right_box, text=risk, text_color="white", fg_color=col, corner_radius=6, padx=8).pack(side="left")

        ctk.CTkLabel(card, text="ÖZET:", font=("Roboto", 12, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=20, pady=(5,0))
        ozet_text = analiz.get("ozet", "Veri yok")
        ctk.CTkLabel(card, text=ozet_text, font=("Roboto", 13), text_color="white", wraplength=900, justify="left").pack(fill="x", padx=20, pady=(0, 10))

        bulgular = analiz.get("bulgular", [])
        if bulgular:
            ctk.CTkLabel(card, text="BULGULAR:", font=("Roboto", 12, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=20, pady=(5,0))
            for b in bulgular:
                ctk.CTkLabel(card, text=f"• {b}", font=("Roboto", 12), text_color="#cbd5e1", wraplength=900, justify="left").pack(anchor="w", padx=25, pady=1)

        oneriler = analiz.get("oneriler", [])
        if oneriler:
            ctk.CTkFrame(card, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=20, pady=10) # Ayırıcı
            ctk.CTkLabel(card, text="ÖNERİLER:", font=("Roboto", 12, "bold"), text_color=COLORS["success"]).pack(anchor="w", padx=20, pady=(5,0))
            for o in oneriler:
                ctk.CTkLabel(card, text=f"🛡️ {o}", font=("Roboto", 12), text_color="#cbd5e1", wraplength=900, justify="left").pack(anchor="w", padx=25, pady=1)
        
        ctk.CTkLabel(card, text="", height=10).pack()

    def view_raw_log(self, scan_id, tool_name):
        scan = database.get_scan_by_id(scan_id)
        out_dir = scan['output_directory']
        if not out_dir or not os.path.exists(out_dir): return messagebox.showerror("Hata", "Log klasörü bulunamadı.")
        
        safe_name = tool_name.lower().replace(" ", "_")
        filename = f"{safe_name}_ciktisi.txt"
        filepath = os.path.join(out_dir, filename)
        
        content = "Dosya bulunamadı."
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
            except Exception as e: content = f"Okuma hatası: {e}"
        else:
            files = glob.glob(os.path.join(out_dir, f"*{safe_name}*.txt"))
            if files:
                try: 
                    with open(files[0], 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
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
        
        # Kenarlıkları kaldır, satır boyunu uzat (rowheight=50)
        style.configure("Treeview", background=COLORS["bg_panel"], foreground="white", 
                        fieldbackground=COLORS["bg_panel"], borderwidth=0, rowheight=50, font=("Roboto", 12))
        
        # Başlık kısmını arka planla aynı yap ki göze batmasın
        style.configure("Treeview.Heading", background=COLORS["bg_main"], foreground=COLORS["text_gray"], 
                        borderwidth=0, font=("Roboto", 12, "bold"))
                        
        # Seçili satır rengini Neon Mor yap
        style.map("Treeview", background=[('selected', COLORS["accent"])])
        
        tree = ttk.Treeview(parent, columns=("ID", "Target", "Status", "Date"), show="headings", style="Treeview")
        tree.heading("ID", text=" ID")
        tree.column("ID", width=60, anchor="center")
        tree.heading("Target", text=" HEDEF")
        tree.column("Target", width=350)
        tree.heading("Status", text=" DURUM")
        tree.column("Status", width=150)
        tree.heading("Date", text=" TARİH")
        tree.column("Date", width=150, anchor="center")
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