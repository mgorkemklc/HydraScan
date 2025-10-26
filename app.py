# app.py (en üstteki importlar)
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import os
import datetime
import database  # <-- BU SATIRI EKLEYİN
import threading # <-- BU SATIRI EKLEYİN
import shutil    # <-- BU SATIRI EKLEYİN
import webbrowser # <-- BU SATIRI EKLEYİN
import concurrent.futures
import logging

# --- HYDRASCAN CORE MODÜLLERİNİ IMPORT EDİN ---
# (Bu dosyaların 'core' klasöründe olduğunu varsayıyoruz)
from core import recon_module
from core import web_app_module
from core import api_module
from core import internal_network_module
from core import cloud_module # (Bunu da ekleyebilirsiniz)
from core import mobile_module # (Bunu da ekleyebilirsiniz)
# from core import wireless_module # (Bunu da ekleyebilirsiniz)
from core import report_module
# --- BİTTİ ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Uygulamanın varsayılan temasını ve renklerini ayarlayalım
ctk.set_appearance_mode("dark")  # "light", "dark", "system"
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class HydraScanApp(ctk.CTk):

    def run_scan_logic(self, scan_id, scan_data):
        """
        GERÇEK TARAMA WORKER'I (PARALEL + İPTAL + İLERLEME).
        """
        current_progress = 0
        current_step_text = "Başlatılıyor..."
        try:
            # --- İptal Kontrolü Fonksiyonu ---
            def check_cancel():
                if self.cancel_requested_map.get(scan_id, False):
                    raise InterruptedError(f"Tarama {scan_id} kullanıcı tarafından iptal edildi.")

            # --- İlerleme Güncelleme Fonksiyonu ---
            def update_scan_progress(value, text):
                nonlocal current_progress, current_step_text
                current_progress = value
                current_step_text = text
                # Ana thread üzerinden GUI'yi güncelle
                self.after(0, self.update_progress, current_progress, current_step_text)


            # --- 1. Hazırlık ---
            update_scan_progress(5, "Hazırlık yapılıyor...")
            self.log_and_update(f"[Scan ID: {scan_id}] Tarama başlatılıyor...")
            # ... (çıktı klasörü oluşturma, DB'ye yazma - AYNI) ...
            base_output_dir = os.path.abspath("scan_outputs")
            scan_output_dir = os.path.join(base_output_dir, f"scan_{scan_id}")
            if not os.path.exists(scan_output_dir): os.makedirs(scan_output_dir)
            database.set_scan_output_directory(scan_id, scan_output_dir)
            database.update_scan_status(scan_id, 'RUNNING')
            self.after(0, self.populate_scan_list)
            # ... (değişkenleri ayarlama - AYNI) ...
            domain_input = scan_data['domain']
            clean_domain = self.get_clean_domain(domain_input)
            internal_ip = scan_data.get('internal_ip')
            api_key = scan_data['gemini_key']
            image_name = "pentest-araci-kali:v1.5"

            check_cancel() # Hazırlık sonrası ilk kontrol

            # --- 2. Tarama Modüllerini PARALEL Çalıştır ---
            update_scan_progress(10, "Ana modüller (paralel) başlatılıyor...")
            self.log_and_update(f"[Scan ID: {scan_id}] Ana modüller (Recon, Web, API) PARALEL olarak başlatılıyor...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                # Her görev için ayrı ilerleme adımı belirleyebiliriz (örn: Recon %30, Web %30, API %10)
                futures.append(executor.submit(recon_module.run_reconnaissance, clean_domain, domain_input, image_name, scan_output_dir))
                futures.append(executor.submit(web_app_module.run_web_tests, domain_input, image_name, scan_output_dir))
                futures.append(executor.submit(api_module.run_api_tests, domain_input, image_name, scan_output_dir))

                # Görevler tamamlandıkça ilerlemeyi güncelle
                completed_tasks = 0
                total_parallel_tasks = len(futures)
                parallel_progress_per_task = 60 / total_parallel_tasks # Paralel görevler toplam %60 ilerleme sağlasın

                for future in concurrent.futures.as_completed(futures):
                    check_cancel() # Her görev bittiğinde iptal kontrolü
                    try:
                        future.result()
                        completed_tasks += 1
                        update_scan_progress(10 + int(completed_tasks * parallel_progress_per_task), f"Ana modül {completed_tasks}/{total_parallel_tasks} tamamlandı...")
                    except Exception as exc:
                        self.log_and_update(f'[Scan ID: {scan_id}] Paralel görevlerden birinde hata oluştu: {exc}')
                        # Hata durumunda ilerlemeyi etkilemeyebiliriz veya %100 FAILED yapabiliriz
                        # Şimdilik devam etsin

            check_cancel() # Paralel görevler bittikten sonra kontrol
            update_scan_progress(70, "Ana modüller tamamlandı.")
            self.log_and_update(f"[Scan ID: {scan_id}] Ana paralel modüller tamamlandı.")

            # --- Sıralı Çalışacak Modüller ---
            if internal_ip:
                check_cancel() # Sıralı modül öncesi kontrol
                update_scan_progress(75, "İç ağ modülü çalışıyor...")
                self.log_and_update(f"[Scan ID: {scan_id}] Ekstra: İç Ağ Modülü (sıralı) çalıştırılıyor...")
                internal_network_module.run_internal_tests(internal_ip, image_name, scan_output_dir)

            # --- Diğer Modüller (Mobil, Kablosuz vb.) ---
            # ... (Buraya if blokları ve check_cancel(), update_scan_progress() ekleyin) ...
            update_scan_progress(80, "Ek modüller tamamlandı.") # Ek modüller bitince ilerlemeyi güncelle

            # --- 3. Raporlama ---
            check_cancel() # Raporlama öncesi kontrol
            update_scan_progress(85, "Raporlama (Gemini AI) başlıyor...")
            self.log_and_update(f"[Scan ID: {scan_id}] Tarama modülleri tamamlandı. Raporlama (Gemini AI) başlıyor...")
            database.update_scan_status(scan_id, 'REPORTING')
            self.after(0, self.populate_scan_list)

            report_local_path = report_module.generate_report(scan_output_dir, domain_input, api_key)

            if report_local_path:
                update_scan_progress(100, "Tamamlandı")
                self.log_and_update(f"[Scan ID: {scan_id}] Rapor başarıyla oluşturuldu: {report_local_path}")
                database.complete_scan(scan_id, report_local_path, "COMPLETED")
            else:
                update_scan_progress(100, "Raporlama Hatası")
                self.log_and_update(f"[Scan ID: {scan_id}] Hata: Rapor oluşturulamadı. Tarama BAŞARISIZ işaretleniyor.")
                database.complete_scan(scan_id, None, "FAILED")

        except InterruptedError as ie: # İptal hatasını yakala
            error_message = f"{ie}"
            self.log_and_update(f"[Scan ID: {scan_id}] {error_message}")
            database.complete_scan(scan_id, None, "FAILED") # Veya "CANCELLED" durumu ekleyebilirsiniz
            update_scan_progress(100, "İptal Edildi")

        except FileNotFoundError as fnf_error:
            error_message = f"KRİTİK HATA: Docker bulunamadı veya başlatılamadı! {fnf_error}"
            self.log_and_update(f"[Scan ID: {scan_id}] {error_message}")
            database.complete_scan(scan_id, None, "FAILED")
            update_scan_progress(100, "Docker Hatası")

        except Exception as e:
            import traceback
            error_message = f"Tarama sırasında kritik hata: {e}\n{traceback.format_exc()}"
            self.log_and_update(f"[Scan ID: {scan_id}] {error_message}")
            database.complete_scan(scan_id, None, "FAILED")
            update_scan_progress(100, "Kritik Hata")

        finally:
            self.after(0, self.on_scan_complete, scan_id)
            
    def __init__(self):
        super().__init__()
        # --- İptal İsteği İçin Bayrak ---
        self.cancel_requested_map = {} # Hangi scan_id'nin iptal istendiğini tutar {scan_id: True}

        # --- Ana Pencere Ayarları ---
        self.title("🐉 HydraScan - Masaüstü Tarama Yöneticisi")
        self.geometry("900x750")

        # --- Veritabanını Başlat ---
        database.init_db()  # <-- BU SATIRI EKLEYİN

        self.cleanup_unfinished_scans()

        # --- Arayüzü Oluştur ---
        self.create_widgets()

    def update_progress(self, value, text):
        """İlerleme çubuğunu ve metnini günceller (Ana thread'den çağrılmalı)."""
        try:
            self.progressbar.set(value / 100) # Değer 0-1 arasında olmalı
            self.progress_label.configure(text=f"Tarama İlerlemesi: {text} ({value}%)")
        except Exception:
            pass # Pencere kapandıysa hata verme

    def on_scan_select(self, event):
        """Kullanıcı tablodan bir tarama seçtiğinde butonları günceller."""
        try:
            selected_item = self.scan_tree.selection()[0]
            values = self.scan_tree.item(selected_item, "values")
            status = values[2] # Durum bilgisi

            if status == "COMPLETED":
                self.open_report_button.configure(state="normal")
                self.cancel_scan_button.configure(state="disabled") # Tamamlanmış iptal edilemez
            elif status == "RUNNING" or status == "REPORTING":
                self.open_report_button.configure(state="disabled")
                self.cancel_scan_button.configure(state="normal") # Çalışan iptal edilebilir
            else: # PENDING, FAILED, INTERRUPTED vb.
                self.open_report_button.configure(state="disabled")
                self.cancel_scan_button.configure(state="disabled")
        except IndexError:
            # Seçim kaldırıldı
            self.open_report_button.configure(state="disabled")
            self.cancel_scan_button.configure(state="disabled")

    def request_cancel_scan(self):
        """'Taramayı İptal Et' butonuna basıldığında iptal isteğini kaydeder."""
        try:
            selected_item = self.scan_tree.selection()[0]
            scan_id = int(selected_item)
            if messagebox.askyesno("Tarama İptal", f"ID: {scan_id} olan taramayı iptal etmek istediğinize emin misiniz?"):
                self.log_and_update(f"[Scan ID: {scan_id}] İptal isteği gönderildi.")
                self.cancel_requested_map[scan_id] = True
                self.cancel_scan_button.configure(text="İptal İsteniyor...", state="disabled") # Butonu geçici olarak devre dışı bırak
        except IndexError:
            messagebox.showwarning("Hata", "Lütfen iptal etmek için çalışan bir tarama seçin.")
        except Exception as e:
            messagebox.showerror("Hata", f"İptal isteği gönderilirken hata oluştu: {e}")

    def cleanup_unfinished_scans(self):
        """Uygulama başlangıcında durumu RUNNING/REPORTING olan taramaları FAILED yapar."""
        try:
            conn = database.get_db_connection()
            # conn.execute'dan önce cursor oluşturmak daha standarttır.
            cursor = conn.cursor()
            cursor.execute("UPDATE scans SET status = 'FAILED', completed_at = ? WHERE status = 'RUNNING' OR status = 'REPORTING'", (datetime.datetime.now(),))
            updated_count = cursor.rowcount # Kaç satırın güncellendiğini al
            conn.commit()
            conn.close()
            if updated_count > 0:
                print(f"[Başlangıç Temizliği] {updated_count} adet tamamlanmamış tarama 'FAILED' olarak işaretlendi.")
        except Exception as e:
            print(f"[Hata] Başlangıç temizliği sırasında veritabanı hatası: {e}")
            # Hata durumunda kullanıcıya bilgi verilebilir
            messagebox.showerror("Veritabanı Hatası", f"Başlangıçta tamamlanmamış taramalar temizlenirken hata oluştu: {e}")    

    def get_clean_domain(self, domain_with_port):
        """Domain'den port numarasını (varsa) ayıklar."""
        if ':' in domain_with_port:
            return domain_with_port.split(':')[0]
        return domain_with_port

    def log_and_update(self, message):
        """Hem log kutusuna hem de (eğer ayarlandıysa) konsola log yazar."""
        logging.info(message) # Konsola log (seviye INFO ise görünür)
        # self.after kullanarak GUI thread'inde güvenle güncelle
        # Not: Eğer worker thread çok sık log yazarsa GUI yavaşlayabilir.
        # Daha gelişmiş bir yöntemde logları bir kuyruğa (queue) atıp
        # GUI thread'i periyodik olarak kuyruktan okuyabilir.
        # Şimdilik bu yöntem yeterli olacaktır.
        try:
            # Pencere kapatıldıktan sonra bu hata verebilir, yakalayalım
            self.after(0, self.add_log, message)
        except Exception:
            pass # Pencere kapandıysa loglamayı atla    

    def create_widgets(self):
        # --- Ana Çerçeve ---
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # --- 1. Başlık Alanı ---
        title_label = ctk.CTkLabel(main_frame, text="🐉 HydraScan", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=10)

            # --- İlerleme Çubuğu ---
        self.progress_label = ctk.CTkLabel(main_frame, text="Tarama İlerlemesi: Beklemede", font=ctk.CTkFont(size=12))
        self.progress_label.pack(fill="x", padx=10, pady=(5,0))
        self.progressbar = ctk.CTkProgressBar(main_frame)
        self.progressbar.pack(fill="x", padx=10, pady=(0, 10))
        self.progressbar.set(0) # Başlangıçta 0

        # --- Durum/Log Alanı (En Alt) ---
        self.log_textbox = ctk.CTkTextbox(main_frame, height=150, state="disabled", text_color="#A9A9A9")
        self.log_textbox.pack(fill="x", padx=5, pady=(0, 5))

        # --- 2. Durum/Log Alanı (En Alt) ---
        # Hata almamak için log kutusunu sekmelerden ÖNCE tanımlıyoruz.
        self.log_textbox = ctk.CTkTextbox(main_frame, height=150, state="disabled", text_color="#A9A9A9")
        self.log_textbox.pack(fill="x", padx=5, pady=(0, 5))
        
        # --- 3. Sekmeli Alan (Yeni Tarama / Gösterge Paneli) ---
        self.tab_view = ctk.CTkTabview(main_frame)
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_yeni_tarama = self.tab_view.add("Yeni Tarama")
        self.tab_dashboard = self.tab_view.add("Gösterge Paneli")
        
        # --- 4. Sekmeleri Doldur ---
        # Artık bu fonksiyonlar 'add_log'u güvenle çağırabilir
        self.create_yeni_tarama_tab(self.tab_yeni_tarama)
        self.create_dashboard_tab(self.tab_dashboard)
        
        # --- 5. İlk Log Mesajı ---
        self.add_log("HydraScan başlatıldı. Lütfen 'Yeni Tarama' sekmesinden bir hedef belirleyin.")

    def get_clean_domain(self, domain_with_port):
        """Domain'den port numarasını (varsa) ayıklar."""
        if ':' in domain_with_port:
            return domain_with_port.split(':')[0]
        return domain_with_port

    def log_and_update(self, message):
        """Hem log kutusuna hem de konsola log yazar."""
        logging.info(message)
        # self.after kullanarak GUI thread'inde güvenle güncelle
        self.after(0, self.add_log, message)    


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
    # ==================================================================
    # GÖSTERGE PANELİ (DASHBOARD) SEKMESİ (DÜZELTİLMİŞ HALİ)
    # ==================================================================
    def create_dashboard_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1) # Tablo alanı (üstte) genişlesin
        tab.grid_columnconfigure(0, weight=1)
        
        # --- 1. ÖNCE TABLO ÇERÇEVESİNİ OLUŞTUR (row=0) ---
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # --- 2. STİLİ OLUŞTUR ---
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
        
        # --- 3. TABLOYU OLUŞTUR (self.scan_tree) ---
        self.scan_tree = ttk.Treeview(tree_frame, columns=("ID", "Hedef", "Durum", "Baslangic"), show="headings")
        self.scan_tree.grid(row=0, column=0, sticky="nsew")

        # --- 4. TABLO AYARLARINI YAP (Başlıklar, Sütunlar) ---
        self.scan_tree.heading("ID", text="ID", anchor="w")
        self.scan_tree.heading("Hedef", text="Hedef", anchor="w")
        self.scan_tree.heading("Durum", text="Durum", anchor="w")
        self.scan_tree.heading("Baslangic", text="Başlangıç Tarihi", anchor="w")

        self.scan_tree.column("ID", width=50, stretch=False, anchor="w")
        self.scan_tree.column("Hedef", width=300, stretch=True, anchor="w")
        self.scan_tree.column("Durum", width=120, stretch=False, anchor="w")
        self.scan_tree.column("Baslangic", width=180, stretch=False, anchor="w")

        # --- 5. KAYDIRMA ÇUBUĞUNU (SCROLLBAR) OLUŞTUR ---
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.scan_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.scan_tree.configure(yscrollcommand=scrollbar.set)
        
        # --- 6. BUTON ÇERÇEVESİNİ OLUŞTUR (row=1) ---
        # (Fazla olan ikinci 'button_frame' bloğu silindi)
        button_frame = ctk.CTkFrame(tab)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        button_frame.grid_columnconfigure(0, weight=1) # Yenile
        button_frame.grid_columnconfigure(1, weight=1) # Raporu Aç
        button_frame.grid_columnconfigure(2, weight=1) # İptal Et
        button_frame.grid_columnconfigure(3, weight=1) # Sil

        self.refresh_button = ctk.CTkButton(button_frame, text="Listeyi Yenile", command=self.populate_scan_list)
        self.refresh_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.open_report_button = ctk.CTkButton(button_frame, text="Raporu Aç", command=self.open_report, state="disabled")
        self.open_report_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.cancel_scan_button = ctk.CTkButton(button_frame, text="Taramayı İptal Et", fg_color="#FFA000", hover_color="#FF8F00", command=self.request_cancel_scan, state="disabled")
        self.cancel_scan_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.delete_scan_button = ctk.CTkButton(button_frame, text="Seçili Taramayı Sil", fg_color="#D32F2F", hover_color="#B71C1C", command=self.delete_scan)
        self.delete_scan_button.grid(row=0, column=3, padx=5, pady=5)

        # --- 7. OLAYI TABLOYA BAĞLA (Tablo artık var) ---
        self.scan_tree.bind("<<TreeviewSelect>>", self.on_scan_select)
        
        # --- 8. LİSTEYİ DOLDUR ---
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
                target=self.run_scan_logic, # <-- FAKE_SCAN_WORKER'I BUNUNLA DEĞİŞTİRİN
                args=(new_scan_id, scan_data),
                daemon=True # Ana program kapanınca thread'in de kapanmasını sağlar
            )
            scan_thread.start()
            
        except Exception as e:
            self.add_log(f"Hata: Tarama başlatılamadı - {e}")
            messagebox.showerror("Veritabanı Hatası", f"Tarama oluşturulurken bir hata oluştu: {e}")

    # ÖNEMLİ: on_scan_complete fonksiyonunu progress bar'ı sıfırlayacak şekilde güncelleyelim
    def on_scan_complete(self, scan_id):
        """Tarama bittiğinde (thread'den çağrılır) arayüzü günceller."""
        self.log_and_update(f"Tarama (ID: {scan_id}) thread'i sonlandı.")
        self.start_button.configure(text="Taramayı Başlat", state="normal")
        # İptal isteğini temizle (varsa)
        if scan_id in self.cancel_requested_map:
            del self.cancel_requested_map[scan_id]
        # İlerleme çubuğunu sıfırla ve metni güncelle
        self.update_progress(0, "Beklemede")
        # Listeyi son kez yenile
        self.populate_scan_list()
        # İptal butonunun durumunu tekrar kontrol et (seçim değişmediyse)
        self.on_scan_select(None) # Seçimi tetikle


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
        try:
            selected_item = self.scan_tree.selection()[0]
            scan_id = int(selected_item)
            
            # Rapor yolunu veritabanından al
            scan_data = database.get_scan_by_id(scan_id)
            if not scan_data:
                messagebox.showerror("Hata", "Tarama veritabanında bulunamadı.")
                return

            report_path = scan_data['report_file_path']
            
            if not report_path or not os.path.exists(report_path):
                self.add_log(f"Rapor dosyası bulunamadı: {report_path}")
                messagebox.showwarning("Rapor Bulunamadı", f"Rapor dosyası '{report_path}' konumunda bulunamadı. Silinmiş olabilir.")
                return

            self.add_log(f"Rapor açılıyor: {report_path}")
            
            # Raporu varsayılan web tarayıcısında aç
            webbrowser.open(f"file://{os.path.realpath(report_path)}")

        except IndexError:
            messagebox.showwarning("Hata", "Lütfen raporunu açmak için tamamlanmış bir tarama seçin.")
        except Exception as e:
            messagebox.showerror("Hata", f"Rapor açılırken bir hata oluştu: {e}")

    def delete_scan(self):
        """Seçili taramayı veritabanından ve diskten (çıktı klasörü) siler."""
        try:
            selected_item = self.scan_tree.selection()[0]
            scan_id = int(selected_item)
            
            scan_data = database.get_scan_by_id(scan_id)
            if not scan_data:
                messagebox.showerror("Hata", "Tarama zaten silinmiş olabilir.")
                self.populate_scan_list()
                return

            if messagebox.askyesno("Tarama Sil", f"ID: {scan_id} ({scan_data['target_full_domain']}) taramasını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz."):
                
                # 1. Diskten çıktı klasörünü sil
                output_dir = scan_data['output_directory']
                if output_dir and os.path.isdir(output_dir):
                    try:
                        shutil.rmtree(output_dir)
                        self.add_log(f"Çıktı klasörü silindi: {output_dir}")
                    except Exception as e:
                        self.add_log(f"Hata: Çıktı klasörü silinemedi: {e}")
                        messagebox.showwarning("Dosya Hatası", f"Çıktı klasörü silinemedi: {e}\nKayıt veritabanından yine de silinecek.")

                # 2. Veritabanından kaydı sil
                database.delete_scan_from_db(scan_id)
                self.add_log(f"Tarama (ID: {scan_id}) veritabanından silindi.")
                
                # 3. Listeyi yenile
                self.populate_scan_list() 
                
        except IndexError:
            messagebox.showwarning("Hata", "Lütfen silmek için bir tarama seçin.")
        except Exception as e:
            messagebox.showerror("Hata", f"Silme işlemi sırasında bir hata oluştu: {e}")


# ==================================================================
# UYGULAMAYI BAŞLAT
# ==================================================================
if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()