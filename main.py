import os
import sys
import json # EKLENDİ
import customtkinter as ctk
import database
from ui.theme import COLORS
from ui.auth_view import AuthView
from ui.sidebar import Sidebar
from ui.views.dashboard_view import DashboardView
from ui.views.web_module_view import WebModuleView 
from ui.views.network_module_view import NetworkModuleView
from ui.views.mobile_module_view import MobileModuleView
from ui.views.api_module_view import ApiModuleView
from ui.views.reports_view import ReportsView
from ui.views.settings_view import SettingsView # EKLENDİ

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".hydrascan", "config.json")

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform v3")
        self.geometry("1400x900")
        ctk.set_appearance_mode("Dark")
        
        # EKLENEN SATIR: Tüm arkaplanı koyu temamıza boyuyoruz
        self.configure(fg_color=COLORS["bg_main"]) 
        
        database.init_db()
        self.load_config() # EKLENDİ:
        self.current_user = None
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.show_auth_view()
    
    # --- AYAR YÖNETİMİ FONKSİYONLARI (EKLENDİ) ---
    def load_config(self):
        self.config = {"api_key": "", "theme": "Dark", "webhook_url": ""} 
        if not os.path.exists(os.path.dirname(CONFIG_FILE)):
            os.makedirs(os.path.dirname(CONFIG_FILE))
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except: pass
        ctk.set_appearance_mode(self.config.get("theme", "Dark"))

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f: 
            json.dump(self.config, f)

    def on_closing(self):
        print("[*] HydraScan kapatılıyor. Arka plan işlemleri sonlandırılıyor...")
        self.destroy()
        os._exit(0)  # Arkada takılı kalan tüm thread'leri temizler ve Python'u kapatır.

    def show_auth_view(self):
        for w in self.container.winfo_children(): w.destroy()
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.auth_view = AuthView(self.container, self)
        self.auth_view.grid(row=0, column=0, sticky="nsew")

    def login_success(self, user_data):
        self.current_user = user_data
        self.init_main_interface()

    def init_main_interface(self):
        self.container.pack_forget() 
        for w in self.container.winfo_children(): 
            w.destroy()
            
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        
        self.sidebar = Sidebar(self.container, self, self.current_user)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.main_area = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        
        # Görünümlerin Yüklenmesi
        self.frames = {}
        self.frames["Dashboard"] = DashboardView(self.main_area, self)
        self.frames["WebModule"] = WebModuleView(self.main_area, self)
        self.frames["NetworkModule"] = NetworkModuleView(self.main_area, self)
        self.frames["MobileModule"] = MobileModuleView(self.main_area, self)
        self.frames["ApiModule"] = ApiModuleView(self.main_area, self)
        self.frames["Reports"] = ReportsView(self.main_area, self)
        
        # SETTINGS GÖRÜNÜMÜNÜ BAĞLADIK (EKLENDİ)
        self.frames["Settings"] = SettingsView(self.main_area, self) 
            
        self.show_view("Dashboard")
        
        self.update_idletasks()
        self.container.pack(fill="both", expand=True)
        
    def show_view(self, view_name):
        for frame in self.frames.values():
            frame.grid_forget()
            
        if view_name in self.frames:
            self.frames[view_name].grid(row=0, column=0, sticky="nsew")
            
            if view_name == "Dashboard" and hasattr(self.frames[view_name], 'refresh_data'):
                self.frames[view_name].refresh_data()
                
            # Raporlar sekmesine tıklandığında listeyi veritabanından çekerek yenile
            if view_name == "Reports" and hasattr(self.frames[view_name], 'refresh_reports_list'):
                self.frames[view_name].refresh_reports_list()
                
        self.sidebar.update_active_btn(view_name)
    def logout(self):
        self.current_user = None
        self.show_auth_view()

if __name__ == "__main__":
    app = HydraScanApp()
    app.mainloop()