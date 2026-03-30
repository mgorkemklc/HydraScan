import customtkinter as ctk
from ui.theme import COLORS
from ui.components import MetricCard

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        # Arkaplanı transparent yapıyoruz ki main.py'deki bg_main rengi arkadan görünsün
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        
        # 1. Metrik Kartları Konteyneri
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 20))
        
        # Özel MetricCard'larımızı kullanıyoruz
        self.card_total = MetricCard(cards, "Toplam Tarama", "0", "Arşivde", "🗃️", COLORS["accent"])
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.card_active = MetricCard(cards, "Aktif Görevler", "0", "Şu an çalışıyor", "⏳", COLORS["warning"])
        self.card_active.pack(side="left", fill="x", expand=True, padx=10)
        
        self.card_risk = MetricCard(cards, "Başarısız/Risk", "0", "İncelenmeli", "🐞", COLORS["danger"])
        self.card_risk.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # 2. Terminal Ekranı
        term_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=10)
        term_frame.pack(fill="x", padx=0, pady=(0, 20))
        
        term_head = ctk.CTkFrame(term_frame, fg_color="transparent")
        term_head.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(term_head, text=">_ CANLI TERMINAL", font=("Consolas", 12, "bold"), text_color=COLORS["success"]).pack(side="left")
        
        self.terminal_box = ctk.CTkTextbox(term_frame, height=150, fg_color=COLORS["log_bg"], text_color=COLORS["terminal_fg"], font=("Consolas", 11))
        self.terminal_box.pack(fill="x", padx=5, pady=5)
        self.terminal_box.insert("0.0", "[*] Sistem hazır. Tarama bekleniyor...\n")

    def refresh_data(self):
        # İleride veritabanı bağlandığında burası kartların sayılarını güncelleyecek
        pass