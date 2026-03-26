import customtkinter as ctk
import threading
from tkinter import filedialog, messagebox
import os
import database
from core.mobile_module import run_mobile_tests

COLORS = {
    "bg_panel": "#1e293b", "bg_input": "#334155", "accent": "#38bdf8", 
    "success": "#22c55e", "danger": "#ef4444", "text_gray": "#94a3b8"
}

class MobileModuleView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.selected_file_path = None
        self.build_ui()

    def build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll, text="📱 Mobil Uygulama Analizi", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # --- Dosya Yükleme Alanı ---
        upload_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        upload_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(upload_frame, text="Uygulama Dosyası (.apk, .ipa, .aab, .zip)", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        btn_frame = ctk.CTkFrame(upload_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.btn_browse = ctk.CTkButton(btn_frame, text="Dosya Seç", fg_color=COLORS["bg_input"], text_color="white", command=self.browse_file)
        self.btn_browse.pack(side="left")
        
        self.lbl_filename = ctk.CTkLabel(btn_frame, text="Henüz bir dosya seçilmedi.", text_color=COLORS["text_gray"])
        self.lbl_filename.pack(side="left", padx=15)

        # --- Analiz Türü Seçimi ---
        tools_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Analiz Yöntemi (ISO 27001 Standartları)", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))

        self.checkbox_vars = {}
        
        self.checkbox_vars["mobsf_sast"] = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(tools_frame, text="Statik Kaynak Kod ve Zafiyet Analizi (SAST - MobSF)", variable=self.checkbox_vars["mobsf_sast"], text_color="white").pack(anchor="w", padx=20, pady=5)
        
        self.checkbox_vars["frida_dast"] = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tools_frame, text="Dinamik Analiz (DAST) ve SSL Pinning Bypass (Sadece Android)", variable=self.checkbox_vars["frida_dast"], text_color="white").pack(anchor="w", padx=20, pady=(5, 15))

        # --- Başlat Butonu ---
        self.btn_start = ctk.CTkButton(self.scroll, text="Analizi Başlat", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], command=self.start_scan_thread)
        self.btn_start.pack(fill="x", pady=20)

        # --- Log Ekranı ---
        log_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        log_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(log_frame, text="İşlem Durumu", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 0))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, height=200, fg_color=COLORS["bg_input"], text_color="#a3e635", font=("Consolas", 12))
        self.log_textbox.pack(fill="x", padx=20, pady=15)
        self.log_textbox.configure(state="disabled")

    def browse_file(self):
        # YALNIZCA BELİRTİLEN UZANTILARA İZİN VER
        filepath = filedialog.askopenfilename(
            title="Uygulama Dosyası Seç", 
            filetypes=(("Mobile Apps", "*.apk;*.ipa;*.aab"), ("Source Code", "*.zip"), ("All Files", "*.*"))
        )
        if filepath:
            self.selected_file_path = filepath
            self.lbl_filename.configure(text=os.path.basename(filepath))

    def append_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_scan_thread(self):
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            return messagebox.showerror("Hata", "Lütfen geçerli bir uygulama dosyası seçin!")

        selected_tools = [tool for tool, var in self.checkbox_vars.items() if var.get()]
        if not selected_tools:
            return messagebox.showerror("Hata", "En az bir analiz yöntemi seçmelisiniz!")

        self.btn_start.configure(state="disabled", text="Analiz Devam Ediyor...", fg_color=COLORS["text_gray"])
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        threading.Thread(target=self.run_scan, args=(self.selected_file_path, selected_tools), daemon=True).start()

    def run_scan(self, file_path, selected_tools):
        try:
            scan_data = {
                "domain": "Mobile_App",
                "internal_ip": None,
                "apk_path": file_path
            }
            scan_id = database.create_scan(scan_data, self.controller.current_user.get('id', 1))
            self.append_log(f"[*] Mobil Analiz ID: {scan_id} oluşturuldu.")

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")
            database.set_scan_output_directory(scan_id, output_dir)
            database.update_scan_status(scan_id, "RUNNING")

            success = run_mobile_tests(
                file_path=file_path,
                output_dir=output_dir,
                selected_tools=selected_tools,
                stream_callback=self.append_log
            )

            if success:
                database.update_scan_status(scan_id, "COMPLETED")
                
        except Exception as e:
            self.append_log(f"\n[!] HATA: {str(e)}")
            try: database.update_scan_status(scan_id, "FAILED")
            except: pass
        finally:
            self.btn_start.configure(state="normal", text="Analizi Başlat", fg_color=COLORS["success"])