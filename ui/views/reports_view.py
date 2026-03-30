import customtkinter as ctk
import os
import platform
import subprocess
from tkinter import messagebox
import database
from core.report_module import generate_pdf_report

COLORS = {
    "bg_panel": "#1e293b", "bg_main": "#0f172a", "accent": "#38bdf8", 
    "success": "#22c55e", "danger": "#ef4444", "text_gray": "#94a3b8"
}

class ReportsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="📄 Raporlar ve Loglar", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        # Tablo Başlıkları
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=5)
        header_frame.pack(fill="x", pady=(0, 10))
        
        headers = [("ID", 50), ("Hedef / Kapsam", 300), ("Tarih", 150), ("Durum", 100), ("İşlemler", 200)]
        for text, width in headers:
            ctk.CTkLabel(header_frame, text=text, font=("Roboto", 14, "bold"), text_color=COLORS["text_gray"], width=width, anchor="w").pack(side="left", padx=10, pady=10)

        # Liste Alanı
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True)

    def refresh_reports_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        user_role = self.controller.current_user.get('role', 'Müşteri')
        user_id = self.controller.current_user.get('id')
        
        # Müşteri sadece kendi taramalarını, Admin herkesinkini görür
        if user_role in ["Superadmin", "Admin", "Pentester"]:
            scans = database.get_all_scans()
        else:
            scans = database.get_all_scans(user_id=user_id)

        if not scans:
            ctk.CTkLabel(self.list_frame, text="Henüz bir tarama kaydı bulunmuyor.", font=("Roboto", 14), text_color=COLORS["text_gray"]).pack(pady=40)
            return

        for scan in scans:
            row_frame = ctk.CTkFrame(self.list_frame, fg_color=COLORS["bg_main"], corner_radius=5)
            row_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(row_frame, text=f"#{scan['id']}", width=50, anchor="w").pack(side="left", padx=10, pady=10)
            ctk.CTkLabel(row_frame, text=scan['target_full_domain'][:40], width=300, anchor="w").pack(side="left", padx=10)
            
            date_str = scan['created_at'].split('.')[0] if scan['created_at'] else "Bilinmiyor"
            ctk.CTkLabel(row_frame, text=date_str, width=150, anchor="w").pack(side="left", padx=10)
            
            status_color = COLORS["success"] if scan['status'] == 'COMPLETED' else COLORS["accent"] if scan['status'] == 'RUNNING' else COLORS["danger"]
            ctk.CTkLabel(row_frame, text=scan['status'], text_color=status_color, width=100, anchor="w", font=("Roboto", 12, "bold")).pack(side="left", padx=10)

            # İşlem Butonları
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent", width=200)
            btn_frame.pack(side="left", padx=10, fill="y")
            
            if scan['status'] == 'COMPLETED':
                btn_pdf = ctk.CTkButton(btn_frame, text="Rapor PDF", width=100, height=30, fg_color=COLORS["accent"], command=lambda s=scan: self.open_or_generate_pdf(s))
                btn_pdf.pack(side="left", padx=5)
            elif scan['status'] == 'RUNNING':
                ctk.CTkLabel(btn_frame, text="Devam Ediyor...", text_color=COLORS["text_gray"]).pack(side="left", padx=5)
            else:
                ctk.CTkLabel(btn_frame, text="Tamamlanmadı", text_color=COLORS["danger"]).pack(side="left", padx=5)

    def open_or_generate_pdf(self, scan_data):
        output_dir = scan_data['output_directory']
        scan_id = scan_data['id']

        # Eğer veritabanında dizin bilgisi boşsa (eski taramalar), dinamik olarak yolu oluştur
        if not output_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")

        # Dizin fiziksel olarak diskte yoksa hata ver (silinmiş olabilir)
        if not os.path.exists(output_dir):
            return messagebox.showerror("Hata", f"Bu taramaya ait çıktı klasörü diskte bulunamadı:\n{output_dir}")
            
        pdf_path = os.path.join(output_dir, f"HydraScan_Report_ID{scan_id}.pdf")
        
        # Eğer PDF henüz oluşturulmadıysa oluştur
        if not os.path.exists(pdf_path):
            try:
                pdf_path = generate_pdf_report(scan_id, scan_data['target_full_domain'], output_dir)
                database.complete_scan(scan_id, pdf_path)
            except Exception as e:
                return messagebox.showerror("Rapor Hatası", f"PDF oluşturulamadı: {str(e)}")

        # Oluşturulan veya var olan PDF'i varsayılan uygulama ile aç
        try:
            if platform.system() == 'Windows':
                os.startfile(pdf_path)
            elif platform.system() == 'Darwin':
                subprocess.call(('open', pdf_path))
            else:
                subprocess.call(('xdg-open', pdf_path))
        except Exception as e:
            messagebox.showerror("Hata", "Dosya açılamadı, dizini manuel kontrol edin.")