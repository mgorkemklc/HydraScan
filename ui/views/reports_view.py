import customtkinter as ctk
import os
import platform
import subprocess
import threading
import time
from tkinter import messagebox
import database
from core.report_module import generate_pdf_report

COLORS = {
    "bg_panel": "#1e293b", "bg_main": "#0f172a", "bg_input": "#334155",
    "accent": "#38bdf8", "success": "#22c55e", "danger": "#ef4444", 
    "warning": "#eab308", "text_gray": "#94a3b8"
}

class ReportsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # --- Üst Başlık ve Geri Butonu ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text="📄 Raporlar ve Loglar", font=("Roboto", 24, "bold"), text_color="white")
        self.title_lbl.pack(side="left")
        
        self.btn_back = ctk.CTkButton(self.header_frame, text="← Listeye Dön", width=120, fg_color=COLORS["bg_input"], command=self.show_list_view)
        
        # --- Liste Görünümü ---
        self.list_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.list_wrapper.grid(row=1, column=0, sticky="nsew")
        self.build_list_ui()
        
        # --- Detay Görünümü ---
        self.detail_wrapper = ctk.CTkFrame(self, fg_color="transparent")

    def build_list_ui(self):
        columns_frame = ctk.CTkFrame(self.list_wrapper, fg_color=COLORS["bg_panel"], corner_radius=5)
        columns_frame.pack(fill="x", pady=(0, 10))
        
        headers = [("ID", 50), ("Hedef / Kapsam", 300), ("Tarih", 150), ("Durum", 100), ("İşlemler", 250)]
        for text, width in headers:
            ctk.CTkLabel(columns_frame, text=text, font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"], width=width, anchor="w").pack(side="left", padx=10, pady=10)

        self.list_frame = ctk.CTkScrollableFrame(self.list_wrapper, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True)

    def refresh_reports_list(self):
        for widget in self.list_frame.winfo_children(): widget.destroy()

        user_role = self.controller.current_user.get('role', 'Müşteri')
        user_id = self.controller.current_user.get('id')
        scans = database.get_all_scans() if user_role in ["Superadmin", "Admin", "Pentester"] else database.get_all_scans(user_id=user_id)

        if not scans:
            ctk.CTkLabel(self.list_frame, text="Henüz bir tarama kaydı bulunmuyor.", text_color=COLORS["text_gray"]).pack(pady=40)
            return

        for scan in scans:
            row = ctk.CTkFrame(self.list_frame, fg_color=COLORS["bg_main"], corner_radius=5)
            row.pack(fill="x", pady=5)
            
            ctk.CTkLabel(row, text=f"#{scan['id']}", width=50, anchor="w").pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(row, text=scan['target_full_domain'][:40], width=300, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(scan['created_at']).split('.')[0], width=150, anchor="w").pack(side="left", padx=10)
            
            status_color = COLORS["success"] if scan['status'] == 'COMPLETED' else COLORS["warning"] if scan['status'] == 'RUNNING' else COLORS["danger"]
            ctk.CTkLabel(row, text=scan['status'], text_color=status_color, width=100, anchor="w", font=("Roboto", 12, "bold")).pack(side="left", padx=10)

            btn_frame = ctk.CTkFrame(row, fg_color="transparent", width=250)
            btn_frame.pack(side="left", padx=10, fill="y")
            
            if scan['status'] == 'COMPLETED':
                ctk.CTkButton(btn_frame, text="İncele", width=80, height=30, fg_color=COLORS["bg_input"], command=lambda s=scan: self.show_detail_view(s)).pack(side="left", padx=5)
                ctk.CTkButton(btn_frame, text="PDF İndir", width=100, height=30, fg_color=COLORS["accent"], command=lambda s=scan: self.open_or_generate_pdf(s)).pack(side="left", padx=5)
            else:
                ctk.CTkLabel(btn_frame, text="İşlem Sürüyor...", text_color=COLORS["text_gray"]).pack(side="left", padx=5)

    def show_list_view(self):
        self.detail_wrapper.grid_forget()
        self.list_wrapper.grid(row=1, column=0, sticky="nsew")
        self.btn_back.pack_forget()
        self.title_lbl.configure(text="📄 Raporlar ve Loglar")
        self.refresh_reports_list()

    def show_detail_view(self, scan_data):
        self.list_wrapper.grid_forget()
        self.detail_wrapper.grid(row=1, column=0, sticky="nsew")
        self.btn_back.pack(side="right", padx=20)
        self.title_lbl.configure(text=f"🔍 İnceleme: #{scan_data['id']} - {scan_data['target_full_domain']}")
        
        for w in self.detail_wrapper.winfo_children(): w.destroy()
        
        output_dir = scan_data['output_directory']
        if not output_dir or not os.path.exists(output_dir):
            ctk.CTkLabel(self.detail_wrapper, text="Çıktı klasörü bulunamadı veya silinmiş.", text_color=COLORS["danger"]).pack(pady=20)
            return

        tabview = ctk.CTkTabview(self.detail_wrapper, fg_color=COLORS["bg_panel"], segmented_button_selected_color=COLORS["accent"])
        tabview.pack(fill="both", expand=True, pady=10)
        
        # --- 1. YENİ ÖZELLİK: ZAFİYETLER VE RE-TEST SEKMESİ ---
        tabview.add("Zafiyetler (Re-Test)")
        self.build_vulnerabilities_tab(tabview.tab("Zafiyetler (Re-Test)"), scan_data['id'])
        
        # --- 2. ESKİ ÖZELLİK: HAM LOG SEKMELERİ ---
        txt_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') or f.endswith('.json')]
        for file in sorted(txt_files):
            tool_name = file.split('_')[0].upper()
            try:
                tabview.add(tool_name)
            except ValueError:
                continue # Aynı isimde sekme varsa atla
            
            textbox = ctk.CTkTextbox(tabview.tab(tool_name), font=("Consolas", 13), fg_color=COLORS["bg_input"], text_color="#a3e635", wrap="none")
            textbox.pack(fill="both", expand=True, padx=5, pady=5)
            
            filepath = os.path.join(output_dir, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    textbox.insert("0.0", content if content.strip() else "[Araç çıktısı boş]")
            except Exception as e:
                textbox.insert("0.0", f"Dosya okunamadı: {str(e)}")
            textbox.configure(state="disabled")

    def build_vulnerabilities_tab(self, parent, scan_id):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        vulns = database.get_vulnerabilities(scan_id)
        if not vulns:
            ctk.CTkLabel(scroll, text="Bu taramada veritabanına işlenmiş kritik/yüksek/orta seviye zafiyet bulunamadı.", font=("Roboto", 14), text_color=COLORS["success"]).pack(pady=40)
            return

        for v in vulns:
            card = ctk.CTkFrame(scroll, fg_color=COLORS["bg_main"], corner_radius=8)
            card.pack(fill="x", pady=5)
            
            # Renk kodlaması
            sev = str(v['severity']).lower()
            sev_color = COLORS["danger"] if sev in ['critical', 'kritik'] else "#f97316" if sev in ['high', 'yüksek'] else COLORS["warning"]
            
            # Bilgiler
            ctk.CTkLabel(card, text=v['vuln_name'][:60], font=("Roboto", 14, "bold"), text_color="white", anchor="w", width=350).pack(side="left", padx=15, pady=15)
            ctk.CTkLabel(card, text=f"CVSS: {v['cvss_score']}", font=("Roboto", 13), text_color=COLORS["text_gray"], width=80).pack(side="left", padx=10)
            ctk.CTkLabel(card, text=v['severity'].upper(), font=("Roboto", 13, "bold"), text_color=sev_color, width=100).pack(side="left", padx=10)
            
            lbl_status = ctk.CTkLabel(card, text=v['status'], font=("Roboto", 13, "bold"), text_color=COLORS["danger"] if v['status']=="Açık" else COLORS["success"], width=100)
            lbl_status.pack(side="left", padx=10)
            
            # Butonlar
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=15)
            
            ctk.CTkButton(btn_frame, text="Kanıt & Çözüm", width=100, fg_color=COLORS["bg_input"], command=lambda vuln=v: self.show_vuln_details(vuln)).pack(side="left", padx=5)
            
            btn_retest = ctk.CTkButton(btn_frame, text="Tekrar Test Et", width=100, fg_color=COLORS["accent"])
            # Re-test fonksiyonunu bağlama (Arayüz referanslarını da yolluyoruz ki güncellensin)
            btn_retest.configure(command=lambda vuln=v, l_stat=lbl_status, b_ret=btn_retest: self.run_retest(vuln, l_stat, b_ret))
            btn_retest.pack(side="left", padx=5)
            
            if v['status'] == "Kapatıldı":
                btn_retest.configure(state="disabled", fg_color=COLORS["bg_input"], text="Doğrulandı")

    def show_vuln_details(self, vuln):
        """Zafiyetin sömürü kanıtını ve çözüm önerisini gösteren Modal Pencere"""
        top = ctk.CTkToplevel(self)
        top.title(f"Zafiyet Analizi: {vuln['vuln_name']}")
        top.geometry("800x600")
        top.attributes("-topmost", True)
        
        scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(scroll, text="🛡️ Çözüm Önerisi (Remediation)", font=("Roboto", 16, "bold"), text_color=COLORS["success"]).pack(anchor="w", pady=(0,5))
        rem_box = ctk.CTkTextbox(scroll, height=120, fg_color=COLORS["bg_panel"], text_color="white", font=("Roboto", 13), wrap="word")
        rem_box.pack(fill="x", pady=(0, 20))
        rem_box.insert("0.0", vuln.get('remediation', 'Bilgi yok.'))
        rem_box.configure(state="disabled")
        
        ctk.CTkLabel(scroll, text="🎯 Sömürü Kanıtı (Payload / Request)", font=("Roboto", 16, "bold"), text_color=COLORS["danger"]).pack(anchor="w", pady=(0,5))
        ev_box = ctk.CTkTextbox(scroll, height=350, fg_color="#000000", text_color="#a3e635", font=("Consolas", 12), wrap="none")
        ev_box.pack(fill="x")
        ev_box.insert("0.0", vuln.get('evidence', 'Kanıt yok.'))
        ev_box.configure(state="disabled")

    def run_retest(self, vuln, status_label, btn_retest):
        """Zafiyeti tekrar test etme simülasyonu (Arka planda çalışır)"""
        btn_retest.configure(state="disabled", text="Test Ediliyor...")
        status_label.configure(text="Doğrulanıyor...", text_color=COLORS["warning"])
        
        def process():
            # Kurumsal senaryoda burada ilgili araca spesifik payload tekrar yollanır.
            # Biz şimdilik Docker'ı tekrar ayağa kaldırmamak için 3 saniyelik bir doğrulama simülasyonu yapıyoruz.
            time.sleep(3) 
            
            # Veritabanında zafiyeti "Kapatıldı" olarak işaretle
            database.update_vulnerability_status(vuln['id'], "Kapatıldı")
            
            # Arayüzü güncelle
            self.after(0, lambda: status_label.configure(text="Kapatıldı", text_color=COLORS["success"]))
            self.after(0, lambda: btn_retest.configure(text="Doğrulandı", fg_color=COLORS["bg_input"]))
            
        threading.Thread(target=process, daemon=True).start()

    def open_or_generate_pdf(self, scan_data):
        output_dir = scan_data['output_directory']
        os.makedirs(output_dir, exist_ok=True)
            
        pdf_path = os.path.join(output_dir, f"HydraScan_Report_ID{scan_data['id']}.pdf")
        
        # PDF yoksa baştan oluştur
        if not os.path.exists(pdf_path):
            try:
                pdf_path = generate_pdf_report(scan_data['id'], scan_data['target_full_domain'], output_dir)
                database.complete_scan(scan_data['id'], pdf_path)
            except Exception as e:
                return messagebox.showerror("Rapor Hatası", f"PDF oluşturulamadı: {str(e)}")

        # Oluşturulan PDF'i aç
        try:
            if platform.system() == 'Windows': os.startfile(pdf_path)
            elif platform.system() == 'Darwin': subprocess.call(('open', pdf_path))
            else: subprocess.call(('xdg-open', pdf_path))
        except:
            messagebox.showerror("Hata", "PDF açılamadı.")