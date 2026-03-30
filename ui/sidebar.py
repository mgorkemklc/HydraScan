import customtkinter as ctk

COLORS = {
    "bg_main": "#0f172a", "bg_panel": "#1e293b", "accent": "#38bdf8", 
    "text_gray": "#94a3b8", "danger": "#ef4444"
}

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, controller, current_user):
        super().__init__(parent, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        self.controller = controller
        self.current_user = current_user
        self.nav_btns = {}
        self.grid_rowconfigure(10, weight=1)
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="HYDRASCAN", font=("Roboto", 22, "bold"), text_color="white").pack(pady=30, padx=20, anchor="w")
        
        role = self.current_user.get('role', 'Müşteri')
        
        self.add_nav_btn("Genel Bakış", "Dashboard")
        
        # Sızma Testi Modülleri (Sadece yetkili rollere görünür)
        if role in ["Superadmin", "Admin", "Pentester"]:
            ctk.CTkLabel(self, text="TARAMA MODÜLLERİ", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
            self.add_nav_btn("Web Uygulama", "WebModule")
            self.add_nav_btn("İç Ağ (Network)", "NetworkModule")
            self.add_nav_btn("Mobil Uygulama", "MobileModule")
            self.add_nav_btn("API Sızma Testi", "ApiModule")
            
        ctk.CTkLabel(self, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
        self.add_nav_btn("Raporlar & Loglar", "Reports")
        
        if role in ["Superadmin", "Admin"]:
            self.add_nav_btn("Ayarlar", "Settings")
            
        # Alt Kısım: Kullanıcı Profili ve Çıkış
        profile = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        
        initials = self.current_user['username'][:2].upper()
        ctk.CTkLabel(profile, text=initials, width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold")).pack(side="left", padx=15, pady=10)
        
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=self.current_user['username'], font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text=role, font=("Roboto", 10), text_color=COLORS["text_gray"]).pack(anchor="w")
        
        ctk.CTkButton(profile, text="Çıkış", width=30, fg_color="transparent", text_color=COLORS["danger"], font=("Roboto", 12), command=self.controller.logout).pack(side="right", padx=10)

    def add_nav_btn(self, text, view_name):
        btn = ctk.CTkButton(
            self, text=text, fg_color="transparent", text_color=COLORS["text_gray"], 
            font=("Roboto", 14), anchor="w", height=40,
            command=lambda: self.controller.show_view(view_name)
        )
        btn.pack(fill="x", padx=15, pady=2)
        self.nav_btns[view_name] = btn

    def update_active_btn(self, active_view):
        for name, btn in self.nav_btns.items():
            if name == active_view:
                btn.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_gray"])