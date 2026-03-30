import customtkinter as ctk
from ui.theme import COLORS

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app_instance, current_user):
        # Arka planı bg_panel (Koyu gri/mavi) yapıyoruz
        super().__init__(parent, fg_color=COLORS["bg_panel"], width=260, corner_radius=0)
        self.app = app_instance
        self.current_user = current_user
        
        # Kullanıcı rolünü al (Eğer giriş yapmamışsa varsayılan atarız)
        self.user_role = current_user.get('role', 'Musteri') if current_user else 'Bilinmiyor'
        
        self.grid_rowconfigure(10, weight=1)
        
        # Logo ve Başlık
        ctk.CTkLabel(self, text="🐉 HYDRASCAN", font=("Roboto", 22, "bold"), text_color="white").pack(pady=30, padx=20, anchor="w")
        
        self.nav_btns = {}
        self.add_nav_btn("Genel Bakış", "📊", "Dashboard")
        
        # Yetkiye Göre Görünmesi Gereken Menüler
        if self.user_role in ["Superadmin", "Admin", "Pentester"]:
            ctk.CTkLabel(self, text="TARAMA MODÜLLERİ", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
            self.add_nav_btn("Web Uygulama", "🌐", "WebModule")
            self.add_nav_btn("İç Ağ (Network)", "🖥️", "NetworkModule")
            self.add_nav_btn("Mobil Uygulama", "📱", "MobileModule")
            self.add_nav_btn("API Güvenliği", "🔗", "ApiModule")
            
        ctk.CTkLabel(self, text="SİSTEM", font=("Roboto", 11, "bold"), text_color=COLORS["text_gray"]).pack(anchor="w", padx=30, pady=(20, 10))
        self.add_nav_btn("Raporlar & Loglar", "📄", "Reports")
        
        if self.user_role in ["Superadmin", "Admin", "Pentester"]:
            self.add_nav_btn("Ayarlar", "⚙️", "Settings")
            
        # Profil Kısmı (En Alt)
        profile = ctk.CTkFrame(self, fg_color=COLORS["bg_main"], height=60)
        profile.pack(side="bottom", fill="x")
        
        username = self.current_user.get('username', 'User') if self.current_user else 'US'
        initials = username[:2].upper()
        
        ctk.CTkLabel(profile, text=initials, width=40, height=40, bg_color=COLORS["accent"], text_color="white", font=("Arial", 16, "bold"), corner_radius=20).pack(side="left", padx=15, pady=10)
        
        info = ctk.CTkFrame(profile, fg_color="transparent")
        info.pack(side="left")
        ctk.CTkLabel(info, text=username, font=("Roboto", 13, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(info, text=self.user_role, font=("Roboto", 10), text_color=COLORS["text_gray"]).pack(anchor="w")
        
        ctk.CTkButton(profile, text="🚪", width=30, fg_color="transparent", text_color=COLORS["danger"], font=("Arial", 16), hover_color=COLORS["bg_panel"], command=self.app.logout).pack(side="right", padx=10)

    def add_nav_btn(self, text, icon, view_name):
        btn = ctk.CTkButton(self, text=f"  {icon}   {text}", anchor="w", fg_color="transparent", 
                            text_color=COLORS["text_gray"], hover_color=COLORS["bg_main"], 
                            height=45, font=("Roboto", 14), 
                            command=lambda: self.app.show_view(view_name))
        btn.pack(fill="x", padx=15, pady=2)
        self.nav_btns[view_name] = btn

    def update_active_btn(self, active_view_name):
        # Tıklanan menüyü vurgular, diğerlerini soluk gri yapar
        for name, btn in self.nav_btns.items():
            if name == active_view_name:
                btn.configure(fg_color=COLORS["bg_main"], text_color=COLORS["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_gray"])