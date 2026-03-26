import customtkinter as ctk
import database

COLORS = {"bg_panel": "#1e293b", "accent": "#38bdf8"}

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.build_ui()

    def build_ui(self):
        ctk.CTkLabel(self, text="Genel Bakış", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x")
        
        self.total_scans_card = self.create_stat_card(stats_frame, "Toplam Tarama", "0")
        self.total_scans_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.create_stat_card(stats_frame, "Tamamlanan İşlemler", "0").pack(side="left", fill="both", expand=True, padx=10)
        self.create_stat_card(stats_frame, "Sistem Durumu", "Aktif").pack(side="left", fill="both", expand=True, padx=(10, 0))

    def create_stat_card(self, parent, title, value):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, height=120)
        ctk.CTkLabel(card, text=title, font=("Roboto", 14), text_color="gray").pack(pady=(20, 5))
        ctk.CTkLabel(card, text=value, font=("Roboto", 32, "bold"), text_color=COLORS["accent"]).pack(pady=(0, 20))
        return card

    def refresh_data(self):
        # Arayüze her dönüldüğünde veritabanından güncel tarama sayılarını çeker
        scans = database.get_all_scans()
        # İlerleyen adımlarda buradaki statik verileri SQLite üzerinden dinamik hale getireceğiz.
        pass