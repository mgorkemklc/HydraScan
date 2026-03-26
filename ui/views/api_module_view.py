import customtkinter as ctk
import threading
from tkinter import filedialog, messagebox
import os
import database
from core.api_module import run_api_tests

COLORS = {
    "bg_panel": "#1e293b", "bg_input": "#334155", "accent": "#38bdf8", 
    "success": "#22c55e", "text_gray": "#94a3b8"
}

class ApiModuleView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.custom_wordlist_path = None
        self.build_ui()

    def build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll, text="🔌 API Sızma Testi", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # --- Hedef ---
        target_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        target_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(target_frame, text="API Endpoint veya Swagger URL", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.entry_target = ctk.CTkEntry(target_frame, placeholder_text="örn: https://api.target.com/v1", height=45, fg_color=COLORS["bg_input"], border_width=0)
        self.entry_target.pack(fill="x", padx=20, pady=(0, 10))

        # --- Wordlist ---
        wl_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
        wl_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkButton(wl_frame, text="API Wordlist Seç (Opsiyonel)", fg_color=COLORS["bg_input"], command=self.select_wordlist).pack(side="left")
        self.lbl_wordlist = ctk.CTkLabel(wl_frame, text="Sistem Varsayılanı Kullanılacak", text_color=COLORS["text_gray"])
        self.lbl_wordlist.pack(side="left", padx=10)

        # --- Araçlar ---
        tools_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        tools_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(tools_frame, text="API Güvenlik Araçları", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 10))

        self.tools = ["kiterunner", "nuclei", "sqlmap", "restler"]
        self.checkbox_vars = {}
        
        grid_frame = ctk.CTkFrame(tools_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        for idx, tool in enumerate(self.tools):
            var = ctk.BooleanVar(value=True if tool in ["kiterunner", "nuclei"] else False)
            self.checkbox_vars[tool] = var
            cb = ctk.CTkCheckBox(grid_frame, text=tool.upper(), variable=var, text_color="white")
            cb.grid(row=0, column=idx, sticky="w", padx=15, pady=10)

        # --- Başlat Butonu ---
        self.btn_start = ctk.CTkButton(self.scroll, text="API Taramasını Başlat", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], command=self.start_scan_thread)
        self.btn_start.pack(fill="x", pady=20)

        # --- Log ---
        log_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        log_frame.pack(fill="x", pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, height=200, fg_color=COLORS["bg_input"], text_color="#a3e635", font=("Consolas", 12))
        self.log_textbox.pack(fill="x", padx=20, pady=15)
        self.log_textbox.configure(state="disabled")

    def select_wordlist(self):
        filepath = filedialog.askopenfilename(title="Wordlist Seç", filetypes=(("Text Files", "*.txt"), ("All Files", "*.*")))
        if filepath:
            self.custom_wordlist_path = filepath
            self.lbl_wordlist.configure(text=os.path.basename(filepath))

    def append_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_scan_thread(self):
        target = self.entry_target.get().strip()
        if not target:
            return messagebox.showerror("Hata", "Lütfen API hedefi belirtin!")

        selected_tools = [tool for tool, var in self.checkbox_vars.items() if var.get()]
        
        self.btn_start.configure(state="disabled", text="Tarama Devam Ediyor...", fg_color=COLORS["text_gray"])
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        threading.Thread(target=self.run_scan, args=(target, selected_tools), daemon=True).start()

    def run_scan(self, target, selected_tools):
        try:
            scan_data = {"domain": target, "internal_ip": None, "apk_path": None}
            scan_id = database.create_scan(scan_data, self.controller.current_user.get('id', 1))
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "scan_outputs", f"scan_{scan_id}")
            database.set_scan_output_directory(scan_id, output_dir)
            database.update_scan_status(scan_id, "RUNNING")

            success = run_api_tests(
                target_input=target,
                output_dir=output_dir,
                selected_tools=selected_tools,
                stream_callback=self.append_log,
                custom_wordlist=self.custom_wordlist_path
            )

            if success:
                database.update_scan_status(scan_id, "COMPLETED")
        except Exception as e:
            self.append_log(f"\n[!] HATA: {str(e)}")
            database.update_scan_status(scan_id, "FAILED")
        finally:
            self.btn_start.configure(state="normal", text="API Taramasını Başlat", fg_color=COLORS["success"])