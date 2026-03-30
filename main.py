import customtkinter as ctk
import database
from ui.auth_view import AuthView
from ui.sidebar import Sidebar
from ui.views.dashboard_view import DashboardView
from ui.views.web_module_view import WebModuleView  # Web modülü import edildi
from ui.views.network_module_view import NetworkModuleView
from ui.views.mobile_module_view import MobileModuleView
from ui.views.api_module_view import ApiModuleView
from ui.views.reports_view import ReportsView

class HydraScanApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HydraScan - Enterprise Security Platform v3")
        self.geometry("1400x900")
        ctk.set_appearance_mode("Dark")
        
        database.init_db()
        self.current_user = None
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        self.show_auth_view()

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
        for w in self.container.winfo_children(): w.destroy()
        
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        
        # Sidebar Entegrasyonu
        self.sidebar = Sidebar(self.container, self, self.current_user)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Ana Çalışma Alanı
        self.main_area = ctk.CTkFrame(self.container, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        
        # Görünümlerin (Views) Yüklenmesi
        self.frames = {}
        
        # 1. Dashboard
        self.frames["Dashboard"] = DashboardView(self.main_area, self)
        # 2. Web Modülü
        self.frames["WebModule"] = WebModuleView(self.main_area, self)
        # 3. İç Ağ Modülü
        self.frames["NetworkModule"] = NetworkModuleView(self.main_area, self)
        # 4. Mobil Modülü
        self.frames["MobileModule"] = MobileModuleView(self.main_area, self)
        # 5. API Modülü
        self.frames["ApiModule"] = ApiModuleView(self.main_area, self)
        # 6. Raporlar Modülü (YENİ EKLENEN)
        self.frames["Reports"] = ReportsView(self.main_area, self)
        
        # Ayarlar için geçici çerçeve
        self.frames["Settings"] = ctk.CTkFrame(self.main_area, fg_color="transparent")
        ctk.CTkLabel(self.frames["Settings"], text="Ayarlar Yapılandırılıyor...", font=("Roboto", 24)).pack(expand=True)
            
        self.show_view("Dashboard")

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