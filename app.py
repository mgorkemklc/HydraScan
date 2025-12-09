import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import datetime
import threading
import json
import concurrent.futures
import logging

# --- VERİTABANI VE MODÜLLER ---
import database
from core import recon_module, web_app_module, api_module, internal_network_module, report_module, mobile_module

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- TASARIM SABİTLERİ (HTML'den Esinlenildi) ---
COLORS = {
    "bg_main": "#0f172a",       # Ana arka plan (Koyu Lacivert)
    "bg_card": "#1e293b",       # Kart arka planı (Daha açık lacivert)
    "bg_card_hover": "#334155", # Kart üzerine gelince
    "accent": "#38bdf8",        # Vurgu rengi (Sky Blue)
    "accent_hover": "#0ea5e9",  # Buton hover rengi
    "text_white": "#f8fafc",    # Beyaz metin
    "text_gray": "#94a3b8",     # Gri metin
    "border": "#475569",        # Kenarlık rengi
    "danger": "#ef4444",        # Kırmızı (Hata/Kritik)
    "success": "#22c55e",       # Yeşil (Başarılı)
    "warning": "#f59e0b"        # Turuncu (Uyarı)
}

# Fontlar
FONT_HEADER = ("Roboto Medium", 24)
FONT_SUBHEADER = ("Roboto Medium", 18)
FONT_BODY = ("Roboto", 13)
FONT_BOLD = ("Roboto", 13, "bold")

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ScanOptionCard(ctk.CTkFrame):
    """HTML'deki 'Tarama Modülü' seçim kartlarını taklit eden özel widget."""
    def __init__(self, parent, title, description, icon, value, variable, command=None):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=12, border_width=2, border_color=COLORS["bg_card"])
        self.value = value
        self.variable = variable
        self.command = command
        
        # Tıklama olaylarını bağla
        self.bind("<Button-1>", self.select)
        
        # İçerik Düzeni
        self.grid_columnconfigure(0, weight=1)
        
        # İkon (Unicode kullanarak)
        self.lbl_icon = ctk.CTkLabel(self, text=icon, font=("Arial", 32), text_color=COLORS["accent"])
        self.lbl_icon.grid(row=0, column=0, pady=(20, 10))
        self.lbl_icon.bind("<Button-1>", self.select)
        
        # Başlık
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 16, "bold"), text_color=COLORS["text_white"])
        self.lbl_title.grid(row=1, column=0, pady=(0, 5))
        self.lbl_title.bind("<Button-1>", self.select)
        
        # Açıklama
        self.lbl_desc = ctk.CTkLabel(self, text=description, font=("Roboto", 11), text_color=COLORS["text_gray"], wraplength=180)
        self.lbl_desc.grid(row=2, column=0, pady=(0, 20), padx=10)
        self.lbl_desc.bind("<Button-1>", self.select)

        # Değişkeni dinle (Dışarıdan değişim olursa güncellemek için)
        if self.variable:
            self.variable.trace_add("write", self.update_state)

    def select(self, event=None):
        if self.variable:
            self.variable.set(self.value)
            if self.command:
                self.command()

    def update_state(self, *args):
        """Seçiliyse kenarlığı ve rengi değiştir."""
        if self.variable.get() == self.value:
            self.configure(border_color=COLORS["accent"], fg_color=COLORS["bg_card_hover"])
        else:
            self.configure(border_color=COLORS["bg_card"], fg_color=COLORS["bg_card"])


class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- PENCERE AYARLARI ---
        self.title("HydraScan - Security Automation Platform")
        self.geometry("1280x850")
        self.configure(fg_color=COLORS["bg_main"])
        
        # İptal ve Durum Yönetimi
        self.cancel_requested_map = {}
        
        # Veritabanı Başlatma
        database.init_db()
        self.cleanup_unfinished_scans()

        # --- ARAYÜZ YERLEŞİMİ (Izgara) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SOL MENÜ (SIDEBAR)
        self.create_sidebar()

        # 2. ANA İÇERİK ALANI
        self.main_content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        # Sayfaları Yönet
        self.frames = {}
        self.create_dashboard_page()
        self.create_new_scan_page()

        # Başlangıç Sayfası
        self.show_frame("Dashboard")

    def create_sidebar(self):
        """base.html'deki sidebar tasarımına benzer yapı."""
        sidebar = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(5, weight=1)

        # Logo Bölümü
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, pady=(40, 20), padx=20, sticky="ew")
        
        icon = ctk.CTkLabel(logo_frame, text="🐉", font=("Arial", 36))
        icon.pack(side="left", padx=(0, 10))
        
        title_box = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="HYDRASCAN", font=("Roboto", 20, "bold"), text_color=COLORS["text_white"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="v2.0 Pro", font=("Roboto", 11), text_color=COLORS["accent"]).pack(anchor="w")

        # Ayırıcı Çizgi
        ctk.CTkFrame(sidebar, height=2, fg_color=COLORS["bg_main"]).grid(row=1, column=0, sticky="ew", padx=20, pady=20)

        # Menü Butonları
        self.btn_dash = self.create_nav_btn(sidebar, "Genel Bakış", "📊", lambda: self.show_frame("Dashboard"))
        self.btn_dash.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.btn_new = self.create_nav_btn(sidebar, "Yeni Tarama", "🚀", lambda: self.show_frame("NewScan"))
        self.btn_new.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Alt Profil Bölümü
        profile_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_main"], corner_radius=10)
        profile_frame.grid(row=6, column=0, padx=20, pady=30, sticky="ew")
        
        ctk.CTkLabel(profile_frame, text="MK", width=40, height=40, corner_radius=20, fg_color=COLORS["accent"], text_color=COLORS["bg_main"], font=("Arial", 16, "bold")).pack(side="left", padx=10, pady=10)
        user_lbls = ctk.CTkFrame(profile_frame, fg_color="transparent")
        user_lbls.pack(side="left")
        ctk.CTkLabel(user_lbls, text="Admin User", font=("Roboto", 13, "bold"), text_color=COLORS["text_white"]).pack(anchor="w")
        ctk.CTkLabel(user_lbls, text="Sistem Yöneticisi", font=("Roboto", 11), text_color=COLORS["success"]).pack(anchor="w")

    def create_nav_btn(self, parent, text, icon, command):
        return ctk.CTkButton(parent, text=f"  {icon}   {text}", command=command,
                             fg_color="transparent", hover_color=COLORS["bg_main"], 
                             text_color=COLORS["text_gray"], anchor="w", height=45, 
                             font=("Roboto", 14, "bold"), corner_radius=8)

    def show_frame(self, name):
        """Sayfa geçişlerini yönetir ve aktif butonu vurgular."""
        for f in self.frames.values(): f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        
        # Buton stillerini güncelle
        if name == "Dashboard":
            self.btn_dash.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])
            self.btn_new.configure(fg_color="transparent", text_color=COLORS["text_gray"])
            self.populate_scan_list()
        else:
            self.btn_dash.configure(fg_color="transparent", text_color=COLORS["text_gray"])
            self.btn_new.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])

    # ==================================================================
    # DASHBOARD SAYFASI (dashboard.html gibi)
    # ==================================================================
    def create_dashboard_page(self):
        page = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.frames["Dashboard"] = page

        # Üst İstatistikler
        stats_grid = ctk.CTkFrame(page, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(0, 25))
        
        self.stat_total = self.create_stat_card(stats_grid, "Toplam Tarama", "0", "📁", COLORS["accent"])
        self.stat_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.stat_active = self.create_stat_card(stats_grid, "Devam Eden", "0", "⚡", COLORS["warning"])
        self.stat_active.pack(side="left", fill="x", expand=True, padx=10)
        
        self.stat_risk = self.create_stat_card(stats_grid, "Kritik Risk", "0", "🛡️", COLORS["danger"])
        self.stat_risk.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Tablo Alanı Başlığı
        action_bar = ctk.CTkFrame(page, fg_color="transparent")
        action_bar.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(action_bar, text="Son Taramalar", font=FONT_SUBHEADER, text_color=COLORS["text_white"]).pack(side="left")
        
        self.btn_refresh = ctk.CTkButton(action_bar, text="↻ Yenile", width=80, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_card_hover"], command=self.populate_scan_list)
        self.btn_refresh.pack(side="right", padx=5)
        
        self.btn_open_rep = ctk.CTkButton(action_bar, text="Raporu Görüntüle", state="disabled", fg_color=COLORS["success"], hover_color="#16a34a", command=self.open_report_gui)
        self.btn_open_rep.pack(side="right", padx=5)

        # Gelişmiş Tablo (Treeview)
        # Treeview için özel stil (Dark mode uyumlu)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background=COLORS["bg_card"], 
                        foreground=COLORS["text_white"], 
                        fieldbackground=COLORS["bg_card"],
                        bordercolor=COLORS["bg_main"],
                        rowheight=40, font=("Roboto", 11))
        style.configure("Treeview.Heading", 
                        background=COLORS["bg_main"], 
                        foreground=COLORS["text_gray"], 
                        font=("Roboto", 12, "bold"), relief="flat")
        style.map("Treeview", background=[('selected', COLORS["accent"])], foreground=[('selected', 'black')])

        # Tablo Çerçevesi (Yuvarlatılmış köşe efekti için)
        table_frame = ctk.CTkFrame(page, fg_color=COLORS["bg_card"], corner_radius=10)
        table_frame.pack(fill="both", expand=True)
        
        self.tree = ttk.Treeview(table_frame, columns=("ID", "Hedef", "Durum", "Tarih"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Hedef", text="HEDEF SİSTEM")
        self.tree.heading("Durum", text="DURUM")
        self.tree.heading("Tarih", text="TARİH")
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Hedef", width=400)
        self.tree.column("Durum", width=150, anchor="center")
        self.tree.column("Tarih", width=200, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def create_stat_card(self, parent, title, value, icon, color):
        """dashboard.html'deki kart tasarımını taklit eder."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12)
        
        # İçerik Konteyner
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Sol Taraf (Metinler)
        text_frame = ctk.CTkFrame(inner, fg_color="transparent")
        text_frame.pack(side="left", fill="y")
        
        ctk.CTkLabel(text_frame, text=title, font=("Roboto", 12), text_color=COLORS["text_gray"]).pack(anchor="w")
        val_lbl = ctk.CTkLabel(text_frame, text=value, font=("Roboto", 28, "bold"), text_color=COLORS["text_white"])
        val_lbl.pack(anchor="w")
        
        # Sağ Taraf (İkon Kutusu)
        icon_box = ctk.CTkFrame(inner, width=50, height=50, corner_radius=10, fg_color=color) # Renkli kutu
        icon_box.pack(side="right", anchor="ne")
        
        ctk.CTkLabel(icon_box, text=icon, font=("Arial", 24), text_color="white").place(relx=0.5, rely=0.5, anchor="center")
        
        card.value_label = val_lbl # Referans
        return card

    # ==================================================================
    # YENİ TARAMA SAYFASI (start_scan_form.html gibi)
    # ==================================================================
    def create_new_scan_page(self):
        page = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.frames["NewScan"] = page

        # Başlık ve Dekoratif Efekt (Basitçe renkli bir başlık ile)
        ctk.CTkLabel(page, text="Yeni Tarama Yapılandırması", font=FONT_HEADER, text_color=COLORS["text_white"]).pack(anchor="w", pady=(0, 20))

        # Ana Form Kartı (start_scan_form.html'deki glass panel)
        form_card = ctk.CTkFrame(page, fg_color=COLORS["bg_card"], corner_radius=15, border_width=1, border_color=COLORS["border"])
        form_card.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Kaydırılabilir İçerik (Eğer ekran küçükse diye)
        scroll = ctk.CTkScrollableFrame(form_card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. HEDEF GİRİŞİ
        ctk.CTkLabel(scroll, text="Hedef (IP veya Domain)", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", pady=(10, 5))
        self.entry_domain = ctk.CTkEntry(scroll, placeholder_text="örn: 192.168.1.1 veya example.com", height=45, font=FONT_BODY, border_color=COLORS["border"])
        self.entry_domain.pack(fill="x", pady=(0, 20))

        # 2. TARAMA MODÜLÜ SEÇİMİ (Kartlı Yapı - start_scan_form.html'deki gibi)
        ctk.CTkLabel(scroll, text="Tarama Modülü", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", pady=(10, 10))
        
        module_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        module_frame.pack(fill="x", pady=(0, 20))
        
        self.scan_type_var = ctk.StringVar(value="basic_scan") # Varsayılan: Basic
        
        # Kart 1: Temel Tarama
        card_basic = ScanOptionCard(
            module_frame, 
            title="Temel Ağ Taraması", 
            description="Hızlı port taraması ve servis tespiti (Nmap Basic).",
            icon="🌐", 
            value="basic_scan", 
            variable=self.scan_type_var
        )
        card_basic.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Kart 2: Kapsamlı Tarama
        card_full = ScanOptionCard(
            module_frame, 
            title="Kapsamlı Tarama", 
            description="Tüm portlar, zafiyet analizi ve detaylı raporlama.",
            icon="☢️", 
            value="full_scan", 
            variable=self.scan_type_var
        )
        card_full.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 3. GELİŞMİŞ AYARLAR (İsteğe Bağlı)
        # --- HATA DÜZELTİLDİ: 'with' bloğu kaldırıldı ---
        adv_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        adv_frame.pack(fill="x", pady=10)
        
        # İç Ağ
        ctk.CTkLabel(adv_frame, text="İç Ağ Aralığı (Opsiyonel)", font=("Roboto", 12, "bold"), text_color=COLORS["text_gray"]).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_internal = ctk.CTkEntry(adv_frame, placeholder_text="192.168.1.0/24", width=300)
        self.entry_internal.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 15))
        
        # Gemini Key
        ctk.CTkLabel(adv_frame, text="Gemini API Anahtarı", font=("Roboto", 12, "bold"), text_color=COLORS["text_gray"]).grid(row=0, column=1, sticky="w", pady=5)
        self.entry_gemini = ctk.CTkEntry(adv_frame, placeholder_text="API Key...", show="*", width=300)
        self.entry_gemini.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 15))

        # APK Seçimi
        apk_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_main"], corner_radius=8)
        apk_frame.pack(fill="x", pady=(0, 20), ipady=5)
        self.btn_apk = ctk.CTkButton(apk_frame, text="APK Dosyası Yükle", command=self.select_apk, fg_color=COLORS["bg_card_hover"], width=150)
        self.btn_apk.pack(side="left", padx=10, pady=10)
        self.lbl_apk = ctk.CTkLabel(apk_frame, text="Dosya seçilmedi", text_color=COLORS["text_gray"])
        self.lbl_apk.pack(side="left", padx=10)
        self.selected_apk = None

        # Durum ve İlerleme
        self.lbl_status = ctk.CTkLabel(scroll, text="Hazır", text_color=COLORS["text_gray"], anchor="e")
        self.lbl_status.pack(fill="x", pady=(10, 0))
        self.progress = ctk.CTkProgressBar(scroll, height=10, progress_color=COLORS["accent"])
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(5, 20))

        # Alt Butonlar (İptal / Başlat)
        btn_box = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_box.pack(fill="x", pady=10)
        
        ctk.CTkButton(btn_box, text="İptal", fg_color="transparent", text_color=COLORS["text_gray"], hover_color=COLORS["bg_main"], width=100, command=lambda: self.show_frame("Dashboard")).pack(side="left")
        
        self.btn_start = ctk.CTkButton(btn_box, text="Taramayı Başlat  🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"], command=self.start_scan_thread)
        self.btn_start.pack(side="right", fill="x", expand=True, padx=(20, 0))

    # ==================================================================
    # FONKSİYONLAR
    # ==================================================================
    def select_apk(self):
        path = filedialog.askopenfilename(filetypes=[("Android App", "*.apk")])
        if path:
            self.selected_apk = path
            self.lbl_apk.configure(text=os.path.basename(path), text_color=COLORS["text_white"])

    def cleanup_unfinished_scans(self):
        try:
            conn = database.get_db_connection()
            conn.cursor().execute("UPDATE scans SET status = 'FAILED' WHERE status IN ('RUNNING', 'REPORTING')")
            conn.commit()
            conn.close()
        except: pass

    def populate_scan_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        scans = database.get_all_scans()
        
        # Sayaçlar
        active = sum(1 for s in scans if s['status'] in ["RUNNING", "REPORTING"])
        failed = sum(1 for s in scans if s['status'] == "FAILED")
        
        self.stat_total.value_label.configure(text=str(len(scans)))
        self.stat_active.value_label.configure(text=str(active))
        self.stat_risk.value_label.configure(text=str(failed)) # Şimdilik Failed'ı risk gibi gösterelim

        for s in scans:
            # Tarih düzeltme
            d = s['created_at']
            try: d = datetime.datetime.strptime(s['created_at'], '%Y-%m-%d %H:%M:%S.%f').strftime('%d %b %H:%M')
            except: pass
            
            # Durum simgesi
            st = s['status']
            icon = "⏳" if st == "PENDING" else "⚡" if st == "RUNNING" else "✅" if st == "COMPLETED" else "❌"
            
            self.tree.insert("", "end", values=(s['id'], s['target_full_domain'], f"{icon} {st}", d))

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            st = self.tree.item(sel[0])['values'][2]
            if "COMPLETED" in st: self.btn_open_rep.configure(state="normal")
            else: self.btn_open_rep.configure(state="disabled")

    def start_scan_thread(self):
        domain = self.entry_domain.get()
        key = self.entry_gemini.get()
        
        if not domain or not key:
            messagebox.showwarning("Eksik Bilgi", "Lütfen Hedef ve Gemini API anahtarını girin.")
            return
            
        self.btn_start.configure(state="disabled", text="Başlatılıyor...")
        self.progress.set(0.05)
        self.lbl_status.configure(text="Sistem hazırlanıyor...")
        
        scan_data = {
            "domain": domain,
            "gemini_key": key,
            "internal_ip": self.entry_internal.get(),
            "apk_path": self.selected_apk,
            "scan_type": self.scan_type_var.get()
        }
        
        scan_id = database.create_scan(scan_data)
        threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data), daemon=True).start()

    def run_scan_logic(self, scan_id, data):
        def ui(p, t): 
            self.progress.set(p)
            self.lbl_status.configure(text=t)

        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            ui(0.1, "Modüller çalışıyor...")
            img = "pentest-araci-kali:v1.5"
            dom = data['domain']
            
            # Paralel İşlemler
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fs = []
                # Basic Scan veya Full Scan ayrımı burada yapılabilir
                fs.append(ex.submit(recon_module.run_reconnaissance, dom, dom, img, out))
                fs.append(ex.submit(web_app_module.run_web_tests, dom, img, out))
                # Full Scan ise API testini de ekle
                if data['scan_type'] == 'full_scan':
                    fs.append(ex.submit(api_module.run_api_tests, dom, img, out))
                
                for f in concurrent.futures.as_completed(fs): pass

            # Ek Modüller
            if data['internal_ip']:
                ui(0.6, "İç ağ taranıyor...")
                internal_network_module.run_internal_tests(data['internal_ip'], img, out)
            
            if data['apk_path']:
                ui(0.7, "Mobil analiz...")
                mobile_module.run_mobile_tests(data['apk_path'], out, img)

            # Raporlama
            ui(0.9, "AI Raporu hazırlanıyor...")
            database.update_scan_status(scan_id, 'REPORTING')
            
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            if path:
                database.complete_scan(scan_id, path, "COMPLETED")
                ui(1.0, "Tamamlandı!")
                messagebox.showinfo("Bitti", "Tarama başarıyla tamamlandı!")
            else:
                database.complete_scan(scan_id, None, "FAILED")
                ui(0.0, "Raporlama Hatası")

        except Exception as e:
            logging.error(e)
            database.complete_scan(scan_id, None, "FAILED")
            ui(0.0, f"Hata: {str(e)}")
            messagebox.showerror("Hata", str(e))
        finally:
            self.btn_start.configure(state="normal", text="Taramayı Başlat  🚀")
            self.populate_scan_list()

    def open_report_gui(self):
        try:
            sel = self.tree.selection()
            if not sel: return
            sid = self.tree.item(sel[0])['values'][0]
            sdata = database.get_scan_by_id(sid)
            path = sdata['report_file_path']
            
            # HTML -> JSON dönüşüm kontrolü (Eski raporlar için)
            if path and path.endswith(".html"): path = path.replace(".html", ".json")
            
            if not path or not os.path.exists(path):
                messagebox.showerror("Hata", "Rapor dosyası bulunamadı.")
                return

            with open(path, 'r', encoding='utf-8') as f: d = json.load(f)
            
            # Rapor Penceresi
            rw = ctk.CTkToplevel(self)
            rw.title(f"Rapor: {d.get('domain')}")
            rw.geometry("1000x800")
            rw.configure(fg_color=COLORS["bg_main"])
            
            # Header
            hf = ctk.CTkFrame(rw, fg_color=COLORS["bg_card"])
            hf.pack(fill="x", padx=20, pady=20)
            ctk.CTkLabel(hf, text=f"🎯 {d.get('domain')}", font=("Roboto", 22, "bold"), text_color="white").pack(anchor="w", padx=20, pady=15)
            
            scr = ctk.CTkScrollableFrame(rw, fg_color="transparent")
            scr.pack(fill="both", expand=True, padx=20, pady=10)
            
            for anz in d.get("analizler", []):
                c = ctk.CTkFrame(scr, fg_color=COLORS["bg_card"], corner_radius=10)
                c.pack(fill="x", pady=10)
                
                risk = anz.get("risk_seviyesi", "").lower()
                rc = COLORS["success"]
                if "yüksek" in risk or "high" in risk: rc = COLORS["warning"]
                if "kritik" in risk or "critical" in risk: rc = COLORS["danger"]
                
                h = ctk.CTkFrame(c, fg_color="transparent")
                h.pack(fill="x", padx=15, pady=10)
                ctk.CTkLabel(h, text=anz.get("arac_adi"), font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
                ctk.CTkLabel(h, text=anz.get("risk_seviyesi").upper(), text_color="white", fg_color=rc, corner_radius=6, padx=8).pack(side="right")
                
                ctk.CTkLabel(c, text=anz.get("ozet"), font=("Roboto", 12), text_color=COLORS["text_white"], wraplength=900, justify="left").pack(anchor="w", padx=15, pady=(0, 15))

        except Exception as e:
            messagebox.showerror("Hata", str(e))

if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()