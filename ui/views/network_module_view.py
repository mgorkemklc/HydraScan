import customtkinter as ctk
from ui.theme import COLORS

class NetworkModuleView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(scroll, text="İç Ağ (Network) Taraması", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        # Hedef Bilgileri
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_panel"], corner_radius=10)
        info_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(info_frame, text="Ağ Hedefi (IP veya CIDR)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(10, 5))
        
        self.entry_net_ip = ctk.CTkEntry(info_frame, placeholder_text="örn: 192.168.1.0/24 veya 10.0.0.5", height=45, fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color="white")
        self.entry_net_ip.pack(fill="x", padx=20, pady=(0, 20))
        
        # Araç Seçimleri
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
            cb = ctk.CTkCheckBox(grid_frm, text=tool.title(), variable=var, text_color="white", fg_color=COLORS["accent"], border_color=COLORS["border"])
            cb.grid(row=r, column=c, sticky="w", padx=10, pady=5)
            c += 1
            if c > 3: 
                c = 0; r += 1

        # Başlat Butonu
        self.btn_net_launch = ctk.CTkButton(scroll, text="AĞ TARAMASINI BAŞLAT 🚀", height=50, font=("Roboto", 16, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=self.launch_scan)
        self.btn_net_launch.pack(fill="x", pady=20)

    def launch_scan(self):
        print(f"[*] Network Taraması başlatılacak: {self.entry_net_ip.get()}")
        # İleride tarama motorunu buraya bağlayacağız