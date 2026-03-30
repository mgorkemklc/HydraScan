import customtkinter as ctk
import threading
from tkinter import messagebox
import os
import database
from core.internal_network_module import run_internal_tests

COLORS = {
    "bg_panel": "#1e293b", "bg_input": "#334155", "accent": "#38bdf8", 
    "success": "#22c55e", "danger": "#ef4444", "text_gray": "#94a3b8"
}

class NetworkModuleView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.build_ui()

    def build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll, text="🖥️ İç Ağ (Network) Sızma Testi", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # --- Hedef Belirleme ---
        target_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        target_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(target_frame, text="Hedef IP veya CIDR Bloğu", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.entry_target = ctk.CTkEntry(target_frame, placeholder_text="örn: 192.168.1.0/24 veya 10.0.0.5", height=45, fg_color=COLORS["bg_input"], border_width=0)
        self.entry_target.pack(fill="x", padx=20, pady=(0, 20))

        # --- Araç Seçimi ---
        tools_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="Tarama ve Analiz Araçları", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))

        self.tools_list = {
            "Ağ Keşfi & Port Tarama": ["masscan", "nmap"],
            "AD & SMB Analizi": ["netexec", "enum4linux"],
            "Zehirleme & Brute Force": ["responder", "hydra"]
        }
        
        self.checkbox_vars = {}
        for category, tools in self.tools_list.items():
            cat_frame = ctk.CTkFrame(tools_frame, fg_color="transparent")
            cat_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(cat_frame, text=category, font=("Roboto", 14, "bold"), text_color="white").pack(anchor="w")
            
            grid_frame = ctk.CTkFrame(cat_frame, fg_color="transparent")
            grid_frame.pack(fill="x", pady=5)
            
            r, c = 0, 0
            for tool in tools:
                default_state = True if tool in ["nmap", "netexec"] else False
                var = ctk.BooleanVar(value=default_state)
                self.checkbox_vars[tool] = var
                cb = ctk.CTkCheckBox(grid_frame, text=tool.upper(), variable=var, text_color="white")
                cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
                c += 1
                if c > 4: 
                    c = 0; r += 1

        # --- Başlat Butonu ---
        self.btn_start = ctk.CTkButton(self.scroll, text="Ağ Taramasını Başlat", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], command=self.start_scan_thread)
        self.btn_start.pack(fill="x", pady=20)

        # --- Log Ekranı ---
        log_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        log_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(log_frame, text="Canlı Terminal Çıktısı", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 0))
        
        self.log_textbox = ctk.CTkTextbox(log_frame, height=200, fg_color=COLORS["bg_input"], text_color="#a3e635", font=("Consolas", 12))
        self.log_textbox.pack(fill="x", padx=20, pady=15)
        self.log_textbox.configure(state="disabled")

    def append_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_scan_thread(self):
        target = self.entry_target.get().strip()
        if not target:
            return messagebox.showerror("Hata", "Lütfen bir hedef IP/CIDR belirtin!")

        selected_tools = [tool for tool, var in self.checkbox_vars.items() if var.get()]
        if not selected_tools:
            return messagebox.showerror("Hata", "En az bir araç seçmelisiniz!")

        self.btn_start.configure(state="disabled", text="Tarama Devam Ediyor...", fg_color=COLORS["text_gray"])
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        threading.Thread(target=self.run_scan, args=(target, selected_tools), daemon=True).start()

    def run_scan(self, target, selected_tools):
        try:
            scan_data = {
                "domain": "Internal_Network",
                "internal_ip": target,
                "apk_path": None
            }
            scan_id = database.create_scan(scan_data, self.controller.current_user.get('id', 1))
            self.append_log(f"[*] İç Ağ Tarama ID: {scan_id} oluşturuldu.")

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")
            database.set_scan_output_directory(scan_id, output_dir)
            database.update_scan_status(scan_id, "RUNNING")

            success = run_internal_tests(
                ip_range=target,
                output_dir=output_dir,
                image_name="pentest-araci-kali:v1.5",
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
            self.btn_start.configure(state="normal", text="Ağ Taramasını Başlat", fg_color=COLORS["success"])