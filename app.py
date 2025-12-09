import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
import os
import datetime
import threading
import json
import concurrent.futures
import logging

# --- SENİN MODÜLLERİN (Veritabanı ve Core) ---
import database
from core import recon_module, web_app_module, api_module, internal_network_module, report_module, mobile_module

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- GÖRSELDEKİ RENK PALETİ (Birebir Uyumlu) ---
COLORS = {
    "bg_main": "#0f172a",       # En koyu arka plan (Slate 900)
    "bg_panel": "#1e293b",      # Kartlar ve Sidebar (Slate 800)
    "accent": "#38bdf8",        # Parlak Mavi (Sky 400)
    "accent_hover": "#0ea5e9",  # Hover Mavisi
    "text_white": "#f1f5f9",    # Beyaz metin
    "text_gray": "#94a3b8",     # Gri metin
    "danger": "#ef4444",        # Kırmızı (Kritik)
    "danger_bg": "rgba(239, 68, 68, 0.2)",
    "success": "#22c55e",       # Yeşil (Başarılı)
    "warning": "#f59e0b",       # Turuncu (Uyarı)
    "running": "#3b82f6",       # Mavi (Çalışıyor)
    "border": "#334155"         # İnce kenarlıklar
}

# Font Ayarları
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MetricCard(ctk.CTkFrame):
    """Dashboard'daki üst bilgi kartları (Görseldeki gibi)"""
    def __init__(self, parent, title, value, sub_text, icon, icon_color):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        
        # İç Padding
        self.grid_columnconfigure(1, weight=1)
        
        # Sol Taraf (Metinler)
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 13), text_color=COLORS["text_gray"])
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=(20, 0), pady=(20, 5))
        
        self.lbl_value = ctk.CTkLabel(self, text=value, font=("Roboto", 32, "bold"), text_color="white")
        self.lbl_value.grid(row=1, column=0, sticky="w", padx=(20, 0), pady=(0, 5))
        
        self.lbl_sub = ctk.CTkLabel(self, text=sub_text, font=("Roboto", 11), text_color=icon_color)
        self.lbl_sub.grid(row=2, column=0, sticky="w", padx=(20, 0), pady=(0, 20))

        # Sağ Taraf (İkon Kutusu)
        self.icon_frame = ctk.CTkFrame(self, width=45, height=45, corner_radius=10, fg_color=COLORS["bg_main"])
        self.icon_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=20, sticky="ne")
        
        self.lbl_icon = ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 20), text_color=icon_color)
        self.lbl_icon.place(relx=0.5, rely=0.5, anchor="center")

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Pencere Ayarları
        self.title("HydraScan - Dashboard")
        self.geometry("1400x900")
        self.configure(fg_color=COLORS["bg_main"])

        # Veritabanı Başlat
        database.init_db()
        self.cleanup_unfinished_scans()

        # --- GRID DÜZENİ ---
        # Sol (Sidebar): Sabit genişlik, Sağ (Content): Esnek
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. SIDEBAR OLUŞTUR
        self.create_sidebar()

        # 2. ANA İÇERİK ALANI (Tüm sayfalar burada değişecek)
        self.main_area = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(1, weight=1) # İçerik alanı

        # Header (Arama çubuğu ve Profil) - Tüm sayfalarda sabit kalabilir veya değişebilir
        self.create_header()

        # Sayfa Yönetimi
        self.frames = {} 
        self.current_frame = None

        # Sayfaları Tanımla
        self.create_dashboard_view()
        self.create_new_scan_view()
        # Rapor sayfası dinamik oluşturulacak

        # Başlangıç
        self.show_view("Dashboard")

    def create_sidebar(self):
        """Görseldeki gibi sol menü"""
        sidebar = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(10, weight=1) # Alt boşluk

        # Logo
        logo_frm = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frm.pack(pady=(30, 40), padx=20, anchor="w")
        ctk.CTkLabel(logo_frm, text="🐉", font=("Arial", 30)).pack(side="left")
        ctk.CTkLabel(logo_frm, text=" HYDRA", font=("Roboto", 22, "bold"), text_color="white").pack(side="left")
        ctk.CTkLabel(logo_frm, text="SCAN", font=("Roboto", 22, "bold"), text_color=COLORS["accent"]).pack(side="left")

        # Menü Öğeleri
        self.nav_btns = {}
        self.add_nav_btn(sidebar, "Genel Bakış", "📊", "Dashboard")
        self.add_nav_btn(sidebar, "Yeni Tarama", "⌖", "NewScan")
        self.add_nav_btn(sidebar, "Raporlar & Loglar", "📄", "Reports") # Henüz aktif değil
        
        # Ayırıcı
        ctk.CTkLabel(sidebar, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(30, 10))
        self.add_nav_btn(sidebar, "Varlık Yönetimi", "server", "Assets")
        self.add_nav_btn(sidebar, "Ayarlar", "⚙️", "Settings")

        # Alt Profil
        profile = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        
        avt = ctk.CTkLabel(profile, text="MK", width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold"))
        avt.pack(side="left", padx=15, pady=10)
        
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text="M. Görkem Kılıç", font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text="Admin", font=("Roboto", 11), text_color=COLORS["text_gray"]).pack(anchor="w")

    def add_nav_btn(self, parent, text, icon, view_name):
        btn = ctk.CTkButton(parent, text=f"  {icon}   {text}", anchor="w",
                            fg_color="transparent", text_color=COLORS["text_gray"],
                            hover_color=COLORS["bg_main"], height=45, font=("Roboto", 14),
                            command=lambda: self.show_view(view_name))
        btn.pack(fill="x", padx=15, pady=2)
        self.nav_btns[view_name] = btn

    def create_header(self):
        """Üst kısımdaki Arama Çubuğu"""
        header = ctk.CTkFrame(self.main_area, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Sayfa Başlığı (Dinamik değişecek)
        self.page_title = ctk.CTkLabel(header, text="Genel Bakış", font=("Roboto", 24, "bold"), text_color="white")
        self.page_title.pack(side="left")

        # Arama Çubuğu (Görseldeki gibi)
        search_frame = ctk.CTkFrame(header, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
        search_frame.pack(side="right", padx=10)
        
        ctk.CTkLabel(search_frame, text="🔍", text_color=COLORS["text_gray"]).pack(side="left", padx=(15, 5))
        ctk.CTkEntry(search_frame, placeholder_text="IP, Domain veya Scan ID...", 
                     fg_color="transparent", border_width=0, width=250, text_color="white").pack(side="left", padx=(0, 10))
        
        # Bildirim Zili
        ctk.CTkButton(header, text="🔔", width=40, fg_color="transparent", hover_color=COLORS["bg_panel"], font=("Arial", 20)).pack(side="right")

    # ==================================================================
    # DASHBOARD GÖRÜNÜMÜ
    # ==================================================================
    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["Dashboard"] = view
        
        # 1. METRİK KARTLARI (Üst Sıra)
        cards_frame = ctk.CTkFrame(view, fg_color="transparent")
        cards_frame.pack(fill="x", pady=(0, 30))
        
        self.card_total = MetricCard(cards_frame, "Toplam Tarama", "0", "⬆ %12 artış", "🗃️", COLORS["accent"])
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.card_risk = MetricCard(cards_frame, "Kritik Açıklar", "0", "⚠ Acil aksiyon", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=10)
        
        self.card_active = MetricCard(cards_frame, "Aktif Görevler", "0", "⚡ Şu an çalışıyor", "⏳", COLORS["running"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=10)
        
        self.card_health = MetricCard(cards_frame, "Sistem Sağlığı", "%98", "Docker aktif", "❤️", COLORS["success"])
        self.card_health.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 2. SON AKTİVİTELER (Tablo)
        table_container = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=1, border_color=COLORS["border"])
        table_container.pack(fill="both", expand=True)
        
        # Tablo Başlığı
        tb_header = ctk.CTkFrame(table_container, fg_color="transparent")
        tb_header.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(tb_header, text="Son Aktiviteler", font=("Roboto", 18, "bold"), text_color="white").pack(side="left")
        
        ctk.CTkButton(tb_header, text="+ Yeni Tarama", font=("Roboto", 13, "bold"), 
                      fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"],
                      command=lambda: self.show_view("NewScan")).pack(side="right")

        # Treeview (Tablo)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["bg_main"], foreground="white", fieldbackground=COLORS["bg_main"], bordercolor=COLORS["bg_panel"], rowheight=45, font=("Roboto", 12))
        style.configure("Treeview.Heading", background=COLORS["bg_panel"], foreground=COLORS["text_gray"], font=("Roboto", 11, "bold"))
        style.map("Treeview", background=[('selected', COLORS["bg_panel"])])

        self.tree = ttk.Treeview(table_container, columns=("Target", "Module", "Status", "Date", "Action"), show="headings")
        self.tree.heading("Target", text="HEDEF")
        self.tree.heading("Module", text="MODÜL")
        self.tree.heading("Status", text="DURUM")
        self.tree.heading("Date", text="TARİH")
        self.tree.heading("Action", text="İŞLEM")
        
        self.tree.column("Target", width=250)
        self.tree.column("Module", width=100, anchor="center")
        self.tree.column("Status", width=150)
        self.tree.column("Date", width=150, anchor="center")
        self.tree.column("Action", width=100, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.tree.bind("<Double-1>", self.on_row_click)

    # ==================================================================
    # YENİ TARAMA SAYFASI
    # ==================================================================
    def create_new_scan_view(self):
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["NewScan"] = view
        
        container = ctk.CTkFrame(view, fg_color=COLORS["bg_panel"], corner_radius=12)
        container.pack(fill="both", expand=True)
        
        # İçerik
        content = ctk.CTkFrame(container, fg_color="transparent")
        content.pack(padx=40, pady=40, fill="x")

        # Hedef Girişi
        ctk.CTkLabel(content, text="Hedef Domain / IP", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.entry_domain = ctk.CTkEntry(content, placeholder_text="örn: example.com", height=50, border_color=COLORS["border"], fg_color=COLORS["bg_main"])
        self.entry_domain.pack(fill="x", pady=(10, 20))

        # Modül Seçimi (Basitleştirilmiş)
        ctk.CTkLabel(content, text="Tarama Modu", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.scan_mode = ctk.StringVar(value="full")
        
        radio_frame = ctk.CTkFrame(content, fg_color="transparent")
        radio_frame.pack(fill="x", pady=(10, 20))
        
        r1 = ctk.CTkRadioButton(radio_frame, text="Hızlı Tarama (Keşif)", variable=self.scan_mode, value="basic", text_color="white", fg_color=COLORS["accent"])
        r1.pack(side="left", padx=(0, 20))
        r2 = ctk.CTkRadioButton(radio_frame, text="Kapsamlı Tarama (Full Pentest)", variable=self.scan_mode, value="full", text_color="white", fg_color=COLORS["accent"])
        r2.pack(side="left")

        # Gelişmiş Ayarlar
        ctk.CTkLabel(content, text="Gemini API Anahtarı", font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.entry_key = ctk.CTkEntry(content, placeholder_text="API Key...", show="*", height=50, border_color=COLORS["border"], fg_color=COLORS["bg_main"])
        self.entry_key.pack(fill="x", pady=(10, 20))

        # Başlat Butonu
        self.btn_launch = ctk.CTkButton(content, text="Taramayı Başlat", height=50, font=("Roboto", 16, "bold"), 
                                        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color=COLORS["bg_main"],
                                        command=self.start_scan)
        self.btn_launch.pack(fill="x", pady=20)
        
        self.scan_status_lbl = ctk.CTkLabel(content, text="", text_color=COLORS["accent"])
        self.scan_status_lbl.pack()

    # ==================================================================
    # RAPOR SAYFASI (GÖMÜLÜ - ENTEGRE)
    # ==================================================================
    def show_report_view(self, scan_id):
        """Uygulamanın içinde Rapor sayfasını oluşturur ve gösterir."""
        
        # Varsa eski rapor sayfasını temizle
        if "ReportView" in self.frames:
            self.frames["ReportView"].destroy()
        
        # Veriyi Çek
        scan = database.get_scan_by_id(scan_id)
        if not scan: return
        
        report_path = scan['report_file_path']
        if report_path and report_path.endswith(".html"): report_path = report_path.replace(".html", ".json")
        
        report_data = {}
        if report_path and os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
        
        # --- SAYFAYI OLUŞTUR ---
        view = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.frames["ReportView"] = view
        
        # 1. Üst Bar (Geri Dön ve Başlık)
        top_bar = ctk.CTkFrame(view, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 20))
        
        btn_back = ctk.CTkButton(top_bar, text="← Geri", width=80, fg_color=COLORS["bg_panel"], command=lambda: self.show_view("Dashboard"))
        btn_back.pack(side="left")
        
        ctk.CTkLabel(top_bar, text=f"Rapor: {scan['target_full_domain']}", font=("Roboto", 20, "bold"), text_color="white").pack(side="left", padx=20)
        
        export_btn = ctk.CTkButton(top_bar, text="PDF İndir", width=100, fg_color=COLORS["bg_panel"], state="disabled") # Şimdilik pasif
        export_btn.pack(side="right")

        # 2. Rapor Özeti (Kartlar)
        if report_data:
            summary_frame = ctk.CTkFrame(view, fg_color="transparent")
            summary_frame.pack(fill="x", pady=(0, 20))
            
            # Risk Analizi (Basit Sayaç)
            total_vulns = 0
            crit = 0
            high = 0
            for item in report_data.get("analizler", []):
                risk = item.get("risk_seviyesi", "").lower()
                total_vulns += len(item.get("bulgular", []))
                if "kritik" in risk or "critical" in risk: crit += 1
                if "yüksek" in risk or "high" in risk: high += 1
            
            # Kartları oluştur (MetricCard kullanarak)
            MetricCard(summary_frame, "Toplam Bulgu", str(total_vulns), "Tüm araçlar", "🔎", COLORS["accent"]).pack(side="left", fill="x", expand=True, padx=(0,10))
            MetricCard(summary_frame, "Kritik Seviye", str(crit), "Acil Düzeltilmeli", "☣️", COLORS["danger"]).pack(side="left", fill="x", expand=True, padx=10)
            MetricCard(summary_frame, "Yüksek Seviye", str(high), "Öncelikli", "🔥", COLORS["warning"]).pack(side="left", fill="x", expand=True, padx=(10,0))

            # 3. Detaylı Rapor Alanı (Scrollable)
            scroll = ctk.CTkScrollableFrame(view, fg_color="transparent")
            scroll.pack(fill="both", expand=True)
            
            for analiz in report_data.get("analizler", []):
                self.create_report_item(scroll, analiz)
        else:
            ctk.CTkLabel(view, text="Rapor verisi bulunamadı veya işleniyor...", font=("Roboto", 16)).pack(pady=50)

        # Görünümü değiştir
        self.show_view("ReportView")
        self.page_title.configure(text="Sızma Testi Raporu")

    def create_report_item(self, parent, analiz):
        """Rapordaki her bir araç çıktısı için kart oluşturur."""
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, border_width=1, border_color=COLORS["border"])
        card.pack(fill="x", pady=10)
        
        # Başlık Satırı
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        
        tool_name = analiz.get("arac_adi", "Bilinmeyen")
        ctk.CTkLabel(header, text=tool_name, font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(side="left")
        
        risk = analiz.get("risk_seviyesi", "Bilgi").upper()
        risk_color = COLORS["success"]
        if "KRITIK" in risk or "CRITICAL" in risk: risk_color = COLORS["danger"]
        elif "YÜKSEK" in risk or "HIGH" in risk: risk_color = COLORS["warning"]
        
        ctk.CTkLabel(header, text=risk, font=("Roboto", 12, "bold"), text_color=risk_color, 
                     fg_color=COLORS["bg_main"], corner_radius=6, width=80, height=30).pack(side="right")

        # Özet Metni
        ctk.CTkLabel(card, text=analiz.get("ozet", ""), font=("Roboto", 13), text_color="white", wraplength=900, justify="left").pack(fill="x", padx=20, pady=(0, 10))
        
        # Bulgular (Varsa)
        if analiz.get("bulgular"):
            f_frame = ctk.CTkFrame(card, fg_color=COLORS["bg_main"], corner_radius=8)
            f_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            ctk.CTkLabel(f_frame, text="TESPİT EDİLEN BULGULAR:", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=10, pady=(10, 5))
            for bulgu in analiz["bulgular"]:
                ctk.CTkLabel(f_frame, text=f"• {bulgu}", font=("Roboto", 12), text_color=COLORS["text_white"], wraplength=850, justify="left").pack(anchor="w", padx=15, pady=2)
            ctk.CTkLabel(f_frame, text="", height=5).pack() # Spacer

    # ==================================================================
    # YARDIMCI FONKSİYONLAR
    # ==================================================================
    def show_view(self, name):
        """Sayfa değiştirici"""
        for frame in self.frames.values():
            frame.grid_forget()
        
        if name in self.frames:
            self.frames[name].grid(row=1, column=0, sticky="nsew")
            self.current_frame = name
            
            # Başlığı Güncelle
            titles = {"Dashboard": "Genel Bakış", "NewScan": "Yeni Tarama Başlat", "Reports": "Rapor Arşivi"}
            if name in titles: self.page_title.configure(text=titles[name])
            
            # Dashboard yenile
            if name == "Dashboard":
                self.refresh_dashboard()

            # Menü buton rengini güncelle
            for btn_name, btn in self.nav_btns.items():
                if btn_name == name:
                    btn.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])
                else:
                    btn.configure(fg_color="transparent", text_color=COLORS["text_gray"])

    def refresh_dashboard(self):
        """Dashboard tablosunu ve metrikleri yeniler"""
        # Tabloyu temizle
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        scans = database.get_all_scans()
        
        # Metrikleri Hesapla
        total = len(scans)
        active = sum(1 for s in scans if s['status'] in ["RUNNING", "REPORTING"])
        failed = sum(1 for s in scans if s['status'] == "FAILED")
        
        # Kartları Güncelle
        self.card_total.lbl_value.configure(text=str(total))
        self.card_active.lbl_value.configure(text=str(active))
        self.card_risk.lbl_value.configure(text=str(failed)) # Şimdilik Failed sayısını risk gibi gösterelim

        # Tabloyu Doldur
        for scan in scans:
            status_raw = scan['status']
            
            # Görsel durum simgeleri
            status_display = f"⚪ {status_raw}"
            if status_raw == "COMPLETED": status_display = "🟢 Tamamlandı"
            elif status_raw == "RUNNING": status_display = "🔵 Taranıyor..."
            elif status_raw == "REPORTING": status_display = "🟣 Raporlanıyor..."
            elif status_raw == "FAILED": status_display = "🔴 Hata"

            date_str = scan['created_at']
            try:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
                date_str = dt.strftime("%d %b, %H:%M")
            except: pass

            action_text = "👁️ İncele" if status_raw == "COMPLETED" else "-"
            
            self.tree.insert("", "end", iid=scan['id'], values=(
                scan['target_full_domain'], 
                "Full_Scan", 
                status_display, 
                date_str, 
                action_text
            ))

    def on_row_click(self, event):
        """Tablo satırına çift tıklandığında raporu aç"""
        selected_item = self.tree.selection()
        if selected_item:
            scan_id = int(selected_item[0])
            scan = database.get_scan_by_id(scan_id)
            if scan['status'] == "COMPLETED":
                self.show_report_view(scan_id)
            else:
                messagebox.showinfo("Bilgi", "Bu tarama henüz tamamlanmadı veya raporu yok.")

    def start_scan(self):
        domain = self.entry_domain.get()
        key = self.entry_key.get()
        
        if not domain or not key:
            messagebox.showwarning("Hata", "Lütfen Domain ve API Key girin.")
            return
            
        self.btn_launch.configure(state="disabled", text="Başlatılıyor...")
        
        scan_data = {
            "domain": domain,
            "gemini_key": key,
            "internal_ip": None,
            "apk_path": None,
            "scan_type": self.scan_mode.get()
        }
        
        scan_id = database.create_scan(scan_data)
        
        # Thread başlat
        threading.Thread(target=self.run_scan_logic, args=(scan_id, scan_data), daemon=True).start()
        
        # Dashboard'a yönlendir
        self.after(1000, lambda: self.show_view("Dashboard"))
        self.btn_launch.configure(state="normal", text="Taramayı Başlat")
        self.entry_domain.delete(0, "end")

    def run_scan_logic(self, scan_id, data):
        # ... (Önceki scan mantığının aynısı) ...
        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            image = "pentest-araci-kali:v1.5"
            domain = data['domain']
            
            with concurrent.futures.ThreadPoolExecutor() as ex:
                fs = [
                    ex.submit(recon_module.run_reconnaissance, domain, domain, image, out),
                    ex.submit(web_app_module.run_web_tests, domain, image, out)
                ]
                for f in concurrent.futures.as_completed(fs): pass

            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, domain, data['gemini_key'])
            
            if path:
                database.complete_scan(scan_id, path, "COMPLETED")
            else:
                database.complete_scan(scan_id, None, "FAILED")
                
        except Exception as e:
            logging.error(e)
            database.complete_scan(scan_id, None, "FAILED")
        finally:
            # GUI güncellemesi için main thread'e sinyal (basitçe refresh)
            pass

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