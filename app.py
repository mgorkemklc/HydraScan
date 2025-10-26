# app.py (en üstteki importlar)
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import os
import datetime
import database  # <-- BU SATIRI EKLEYİN
import threading # <-- BU SATIRI EKLEYİN
import shutil    # <-- BU SATIRI EKLEYİN
import webbrowser # <-- BU SATIRI EKLEYİN

# Uygulamanın varsayılan temasını ve renklerini ayarlayalım
ctk.set_appearance_mode("dark")  # "light", "dark", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class HydraScanApp(ctk.CTk):

    def fake_scan_worker(self, scan_id, scan_data):
        """
        (GEÇİCİ FONKSİYON) 
        Gerçek tarama mantığını (Docker, modüller, raporlama) simüle eder.
        """
        import time
        try:
            self.add_log(f"[Scan ID: {scan_id}] Tarama 'RUNNING' olarak işaretleniyor...")
            database.update_scan_status(scan_id, 'RUNNING')
            
            # Arayüzü ana thread üzerinden güvenle güncelle
            self.after(0, self.populate_scan_list) 

            # Simülasyon: 5 saniye boyunca "çalışıyor" gibi yap
            self.add_log(f"[Scan ID: {scan_id}] Tarama modülleri çalışıyor...")
            time.sleep(5) 
            
            # Simülasyon: Raporlama yapılıyor
            self.add_log(f"[Scan ID: {scan_id}] Raporlama 'REPORTING' olarak işaretleniyor...")
            database.update_scan_status(scan_id, 'REPORTING')
            self.after(0, self.populate_scan_list)
            time.sleep(2)

            # Simülasyon: Tarama bitti
            fake_report_path = f"scan_outputs/scan_{scan_id}/pentest_raporu_v2.html"
            database.complete_scan(scan_id, fake_report_path, "COMPLETED")
            self.add_log(f"[Scan ID: {scan_id}] Tarama 'COMPLETED' olarak işaretlendi.")
            
        except Exception as e:
            self.add_log(f"[Scan ID: {scan_id}] Hata oluştu: {e}")
            database.complete_scan(scan_id, None, "FAILED")
        
        # Tarama bitince (başarılı veya hatalı) arayüzü son kez güncelle
        self.after(0, self.on_scan_complete, scan_id)

    def __init__(self):
        super().__init__()

        # --- Ana Pencere Ayarları ---
        self.title("🐉 HydraScan - Masaüstü Tarama Yöneticisi")
        self.geometry("900x750")

        # --- Veritabanını Başlat ---
        database.init_db()  # <-- BU SATIRI EKLEYİN

        # --- Arayüzü Oluştur ---
        self.create_widgets()

    def create_widgets(self):
        # --- Ana Çerçeve ---
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 1. Başlık Alanı ---
        title_label = ctk.CTkLabel(main_frame, text="🐉 HydraScan", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=10)

        # --- 2. Sekmeli Alan (Yeni Tarama / Gösterge Paneli) ---
        self.tab_view = ctk.CTkTabview(main_frame)
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_yeni_tarama = self.tab_view.add("Yeni Tarama")
        self.tab_dashboard = self.tab_view.add("Gösterge Paneli")
        
        # --- Sekmeleri Doldur ---
        self.create_yeni_tarama_tab(self.tab_yeni_tarama)
        self.create_dashboard_tab(self.tab_dashboard)
        
        # --- 3. Durum/Log Alanı (En Alt) ---
        self.log_textbox = ctk.CTkTextbox(main_frame, height=150, state="disabled", text_color="#A9A9A9")
        self.log_textbox.pack(fill="x", padx=5, pady=(0, 5))
        self.add_log("HydraScan başlatıldı. Lütfen 'Yeni Tarama' sekmesinden bir hedef belirleyin.")


    # ==================================================================
    # YENİ TARAMA SEKMESİ
    # ==================================================================
    def create_yeni_tarama_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        
        # --- Temel Hedefler Çerçevesi ---
        temel_frame = ctk.CTkFrame(tab)
        temel_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        temel_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(temel_frame, text="Temel Hedefler", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(5, 10))

        ctk.CTkLabel(temel_frame, text="Hedef Domain:").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.entry_domain = ctk.CTkEntry(temel_frame, placeholder_text="örn: site.com:8080")
        self.entry_domain.grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(temel_frame, text="İç Ağ IP Aralığı:").grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.entry_internal_ip = ctk.CTkEntry(temel_frame, placeholder_text="Opsiyonel (örn: 192.168.1.0/24)")
        self.entry_internal_ip.grid(row=2, column=1, sticky="ew", padx=10, pady=5)

        # --- Gelişmiş Modüller Çerçevesi ---
        gelismis_frame = ctk.CTkFrame(tab)
        gelismis_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        gelismis_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(gelismis_frame, text="Gelişmiş Modüller (Opsiyonel)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, pady=(5, 10))
        
        # Mobil (APK)
        ctk.CTkLabel(gelismis_frame, text="Mobil (.apk):").grid(row=1, column=0, sticky="e", padx=10, pady=5)
        self.apk_button = ctk.CTkButton(gelismis_frame, text="APK Dosyası Seç...", command=self.select_apk_file, width=150)
        self.apk_button.grid(row=1, column=1, padx=(10, 5), pady=5, sticky="w")
        self.apk_path_label = ctk.CTkLabel(gelismis_frame, text="Dosya seçilmedi", text_color="gray")
        self.apk_path_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.selected_apk_path = None # Seçilen dosya yolunu burada saklayacağız

        # Kablosuz
        ctk.CTkLabel(gelismis_frame, text="Kablosuz Arayüz:").grid(row=2, column=0, sticky="e", padx=10, pady=5)
        self.entry_wifi_iface = ctk.CTkEntry(gelismis_frame, placeholder_text="örn: wlan0")
        self.entry_wifi_iface.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(gelismis_frame, text="Hedef BSSID:").grid(row=3, column=0, sticky="e", padx=10, pady=5)
        self.entry_wifi_bssid = ctk.CTkEntry(gelismis_frame, placeholder_text="örn: AA:BB:CC:11:22:33")
        self.entry_wifi_bssid.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(gelismis_frame, text="Hedef Kanal:").grid(row=4, column=0, sticky="e", padx=10, pady=5)
        self.entry_wifi_channel = ctk.CTkEntry(gelismis_frame, placeholder_text="örn: 6")
        self.entry_wifi_channel.grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=5)

        # --- Raporlama & Başlatma Çerçevesi ---
        rapor_frame = ctk.CTkFrame(tab)
        rapor_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        rapor_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(rapor_frame, text="Raporlama Ayarı").grid(row=0, column=0, sticky="e", padx=10, pady=5)
        self.entry_gemini_key = ctk.CTkEntry(rapor_frame, placeholder_text="Gemini API Anahtarınızı buraya girin (Raporlama için zorunlu)", show="*")
        self.entry_gemini_key.grid(row=0, column=1, sticky="ew", padx=10, pady=5)

        # --- Başlat Butonu ---
        self.start_button = ctk.CTkButton(tab, text="Taramayı Başlat", font=ctk.CTkFont(size=16, weight="bold"), height=40, command=self.start_scan_thread)
        self.start_button.grid(row=3, column=0, sticky="ews", padx=10, pady=10)


    # ==================================================================
    # GÖSTERGE PANELİ (DASHBOARD) SEKMESİ
    # ==================================================================
    def create_dashboard_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # --- Tablo Çerçevesi ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- Stil (CustomTkinter temasına uyması için) ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
                        background="#2b2b2b", 
                        foreground="white", 
                        fieldbackground="#2b2b2b", 
                        bordercolor="#2b2b2b",
                        rowheight=25)
        style.map('Treeview', background=[('selected', '#3471CD')]) # Seçim rengi
        style.configure("Treeview.Heading", 
                        background="#565b5e", 
                        foreground="white", 
                        font=('Calibri', 12, 'bold'))
        style.map("Treeview.Heading",
                  background=[('active', '#3471CD')])
        
        # --- Tablo (Treeview) ---
        self.scan_tree = ttk.Treeview(tree_frame, columns=("ID", "Hedef", "Durum", "Baslangic"), show="headings")
        self.scan_tree.grid(row=0, column=0, sticky="nsew")

        # Sütun Başlıkları
        self.scan_tree.heading("ID", text="ID", anchor="w")
        self.scan_tree.heading("Hedef", text="Hedef", anchor="w")
        self.scan_tree.heading("Durum", text="Durum", anchor="w")
        self.scan_tree.heading("Baslangic", text="Başlangıç Tarihi", anchor="w")

        # Sütun Genişlikleri
        self.scan_tree.column("ID", width=50, stretch=False, anchor="w")
        self.scan_tree.column("Hedef", width=300, stretch=True, anchor="w")
        self.scan_tree.column("Durum", width=120, stretch=False, anchor="w")
        self.scan_tree.column("Baslangic", width=180, stretch=False, anchor="w")

        # Dikey Kaydırma Çubuğu
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.scan_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.scan_tree.configure(yscrollcommand=scrollbar.set)
        
        # --- Buton Çerçevesi ---
        button_frame = ctk.CTkFrame(tab)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)
        button_frame.grid_columnconfigure(2, weight=1)

        self.refresh_button = ctk.CTkButton(button_frame, text="Listeyi Yenile", command=self.populate_scan_list)
        self.refresh_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.open_report_button = ctk.CTkButton(button_frame, text="Raporu Aç", command=self.open_report, state="disabled")
        self.open_report_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.delete_scan_button = ctk.CTkButton(button_frame, text="Seçili Taramayı Sil", fg_color="#D32F2F", hover_color="#B71C1C", command=self.delete_scan)
        self.delete_scan_button.grid(row=0, column=2, padx=5, pady=5)

        # Tabloya tıklandığında butonları yönet
        self.scan_tree.bind("<<TreeviewSelect>>", self.on_scan_select)
        
        # --- Test Verisi Yükle (Başlangıç için) ---
        self.populate_scan_list()


    # ==================================================================
    # FONKSİYONLAR (Şimdilik boş, sonradan doldurulacak)
    # ==================================================================
    
    def add_log(self, message):
        """Arayüzdeki log kutusuna mesaj ekler."""
        self.log_textbox.configure(state="normal")
        # DÜZELTME: ctk. kaldırıldı
        self.log_textbox.insert("end", f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end") # Otomatik aşağı kaydır

    def select_apk_file(self):
        """Mobil APK dosyası seçmek için bir dosya diyaloğu açar."""
        file_path = filedialog.askopenfilename(
            title="Bir .apk dosyası seçin",
            filetypes=(("Android Paketleri", "*.apk"), ("Tüm Dosyalar", "*.*"))
        )
        if file_path:
            self.selected_apk_path = file_path
            self.apk_path_label.configure(text=os.path.basename(file_path), text_color="white")
            self.add_log(f"Mobil tarama için dosya seçildi: {file_path}")
        else:
            self.selected_apk_path = None
            self.apk_path_label.configure(text="Dosya seçilmedi", text_color="gray")

    def start_scan_thread(self):
        """
        'Taramayı Başlat' butonuna basıldığında tetiklenir.
        Girdileri doğrular, DB'ye kaydeder ve taramayı ayrı bir thread'de başlatır.
        """
        self.add_log("Tarama isteği alındı, girdiler doğrulanıyor...")
        
        domain = self.entry_domain.get()
        gemini_key = self.entry_gemini_key.get()
        
        if not domain or not gemini_key:
            messagebox.showerror("Eksik Bilgi", "Lütfen 'Hedef Domain' ve 'Gemini API Anahtarı' alanlarını doldurun.")
            self.add_log("Hata: Hedef Domain veya Gemini API anahtarı eksik.")
            return

        # --- Tüm girdileri topla ---
        scan_data = {
            "domain": domain,
            "gemini_key": gemini_key, # Gemini anahtarını DB'ye kaydetmiyoruz, sadece worker'a yollayacağız
            "internal_ip": self.entry_internal_ip.get() or None,
            "apk_path": self.selected_apk_path,
            "wifi_iface": self.entry_wifi_iface.get() or None,
            "wifi_bssid": self.entry_wifi_bssid.get() or None,
            "wifi_channel": self.entry_wifi_channel.get() or None
        }
        
        try:
            # 1. Taramayı veritabanına kaydet
            new_scan_id = database.create_scan(scan_data)
            self.add_log(f"Hedef: {domain} için tarama ID {new_scan_id} ile veritabanına eklendi.")
            
            # 2. Arayüzü güncelle ve Dashboard'a geç
            self.start_button.configure(text="Tarama Çalışıyor...", state="disabled")
            self.tab_view.set("Gösterge Paneli")
            self.populate_scan_list() # Listeyi anında yenile

            # 3. BURASI ÇOK ÖNEMLİ: Asıl işi (tarama) ayrı bir thread'de başlat
            # Arayüzün donmaması için 'target' olarak ana tarama mantığını vereceğiz
            # Şimdilik, sadece 5 saniye uyuyan sahte bir worker başlatalım
            
            # (Gelecek adımda 'target'ı 'self.run_scan_logic' ile değiştireceğiz)
            scan_thread = threading.Thread(
                target=self.fake_scan_worker, # <-- ŞİMDİLİK SAHTE WORKER
                args=(new_scan_id, scan_data)
            )
            scan_thread.start()
            
        except Exception as e:
            self.add_log(f"Hata: Tarama başlatılamadı - {e}")
            messagebox.showerror("Veritabanı Hatası", f"Tarama oluşturulurken bir hata oluştu: {e}")can_id)

    def on_scan_complete(self, scan_id):
        """Tarama bittiğinde (thread'den çağrılır) arayüzü günceller."""
        self.add_log(f"Tarama (ID: {scan_id}) arayüz güncellemesi tamamlandı.")
        self.start_button.configure(text="Taramayı Başlat", state="normal")
        self.populate_scan_list() # Listeyi son kez yenile


    def populate_scan_list(self):
        """
        db.sqlite3 dosyasından taramaları okur ve tabloyu doldurur.
        """
        # Önce mevcut tabloyu temizle
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)
            
        try:
            # Veritabanından TÜM taramaları çek
            all_scans = database.get_all_scans() 
            
            if not all_scans:
                self.add_log("Veritabanında hiç tarama kaydı bulunamadı.")
                return

            # self.report_paths = {} # Rapor yollarını saklamak için (buna gerek kalmadı)

            for scan in all_scans:
                # Veritabanı satırını (dict) al
                scan_id = scan['id']
                target = scan['target_full_domain']
                status = scan['status']
                # Tarih formatlaması
                created_time = datetime.datetime.strptime(scan['created_at'], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d %H:%M')

                # Duruma göre satıra etiket (renk) ata
                tag = ""
                if status == "COMPLETED":
                    tag = "completed"
                elif status == "RUNNING" or status == "REPORTING":
                    tag = "running"
                elif status == "FAILED":
                    tag = "failed"
                else:
                    tag = "pending" # PENDING durumu

                # Veriyi tabloya ekle
                self.scan_tree.insert("", "end", iid=scan_id, values=(scan_id, target, status, created_time), tags=(tag,))
                
            # Etiketlerin renklerini ayarla (Mevcut kodunuzda vardı, tekrar tanımlayalım)
            self.scan_tree.tag_configure("completed", foreground="#4CAF50") # Yeşil
            self.scan_tree.tag_configure("running", foreground="#2196F3")   # Mavi
            self.scan_tree.tag_configure("failed", foreground="#F44336")    # Kırmızı
            self.scan_tree.tag_configure("pending", foreground="#FF9800")  # Turuncu

        except Exception as e:
            self.add_log(f"Dashboard yenilenirken hata oluştu: {e}")
            messagebox.showerror("Veritabanı Hatası", f"Taramalar çekilirken bir hata oluştu: {e}")

    def on_scan_select(self, event):
        """Kullanıcı tablodan bir tarama seçtiğinde çalışır."""
        try:
            selected_item = self.scan_tree.selection()[0] # Seçilen ilk öğe (ID)
            values = self.scan_tree.item(selected_item, "values")
            status = values[2] # Durum bilgisi
            
            # Raporu Aç butonu sadece 'Tamamlandı' ise aktif olsun
            if status == "COMPLETED":
                self.open_report_button.configure(state="normal")
            else:
                self.open_report_button.configure(state="disabled")
        except IndexError:
            # Seçim kaldırıldı
            self.open_report_button.configure(state="disabled")

    def open_report(self):
        """'Raporu Aç' butonuna basıldığında ilgili HTML raporunu açar."""
        selected_item = self.scan_tree.selection()[0]
        #
        # BURASI ÇOK ÖNEMLİ:
        # Burada, seçili taramanın (scan_id) rapor dosya yolunu (report_file_path)
        # veritabanından almanız ve `os.startfile()` veya `webbrowser.open()`
        # ile açmanız gerekecek.
        #
        
        # Sahte rapor yolu:
        report_path = f"raporlar/google_com/report.html" # Bu yolu veritabanından almalısınız
        self.add_log(f"Rapor açılıyor: {report_path}")
        
        # import webbrowser
        # webbrowser.open(f"file://{os.path.realpath(report_path)}")
        messagebox.showinfo("Rapor Aç", f"(Simülasyon) Rapor açılıyor:\n{report_path}")

    def delete_scan(self):
        """Seçili taramayı ve ilgili dosyaları siler."""
        try:
            selected_item = self.scan_tree.selection()[0]
            if messagebox.askyesno("Tarama Sil", f"ID: {selected_item} olan taramayı silmek istediğinize emin misiniz?\nBu işlem geri alınamaz."):
                #
                # BURASI ÇOK ÖNEMLİ:
                # 1. Veritabanından bu scan_id'ye ait kaydı silin (`database.py`)
                # 2. Bu taramanın çıktı klasörünü (örn: `raporlar/scan_ID`) diskten silin (`shutil.rmtree`)
                #
                self.add_log(f"Tarama (ID: {selected_item}) silindi.")
                self.populate_scan_list() # Listeyi yenile
        except IndexError:
            messagebox.showwarning("Hata", "Lütfen silmek için bir tarama seçin.")


# ==================================================================
# UYGULAMAYI BAŞLAT
# ==================================================================
if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()