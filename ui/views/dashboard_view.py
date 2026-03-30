import customtkinter as ctk
import database
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

COLORS = {"bg_panel": "#1e293b", "accent": "#38bdf8", "text_gray": "#94a3b8"}

class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.canvas = None
        self.build_ui()

    def build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll, text="📊 Genel Bakış ve Sistem Durumu", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        # --- İstatistik Kartları ---
        stats_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=10)
        
        self.card_total = self.create_stat_card(stats_frame, "Toplam Tarama", "0")
        self.card_total.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.card_completed = self.create_stat_card(stats_frame, "Tamamlanan İşlemler", "0")
        self.card_completed.pack(side="left", fill="both", expand=True, padx=10)
        
        self.create_stat_card(stats_frame, "Sistem Durumu", "Aktif").pack(side="left", fill="both", expand=True, padx=(10, 0))

        # --- İnteraktif Grafik Alanı (Eski Gücümüz) ---
        self.chart_frame = ctk.CTkFrame(self.scroll, fg_color=COLORS["bg_panel"], corner_radius=10, height=400)
        self.chart_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(self.chart_frame, text="Zafiyet Dağılım Grafiği", font=("Roboto", 16, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(15, 0))

    def create_stat_card(self, parent, title, value):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_panel"], corner_radius=10, height=120)
        ctk.CTkLabel(card, text=title, font=("Roboto", 14), text_color=COLORS["text_gray"]).pack(pady=(20, 5))
        lbl_val = ctk.CTkLabel(card, text=value, font=("Roboto", 32, "bold"), text_color=COLORS["accent"])
        lbl_val.pack(pady=(0, 20))
        card.lbl_val = lbl_val  # Değeri sonradan güncellemek için referans tutuyoruz
        return card

    def refresh_data(self):
        # Arayüze her dönüldüğünde veritabanından güncel verileri çeker
        user_role = self.controller.current_user.get('role', 'Müşteri')
        user_id = self.controller.current_user.get('id')
        
        scans = database.get_all_scans() if user_role in ["Superadmin", "Admin", "Pentester"] else database.get_all_scans(user_id=user_id)
        
        total = len(scans)
        completed = len([s for s in scans if s['status'] == 'COMPLETED'])
        
        self.card_total.lbl_val.configure(text=str(total))
        self.card_completed.lbl_val.configure(text=str(completed))

        self.draw_chart(scans)

    def draw_chart(self, scans):
        if self.canvas:
            self.canvas.get_tk_widget().destroy()

        # Örnek statik veri (Kısım 3 CVSS modülüne geçtiğimizde burası veritabanından dinamik dolacak)
        labels = ['Kritik', 'Yüksek', 'Orta', 'Düşük']
        sizes = [5, 12, 25, 40] if scans else [0, 0, 0, 1]
        colors = ['#ef4444', '#f97316', '#eab308', '#22c55e'] if scans else ['#334155']*4

        fig = Figure(figsize=(6, 4), dpi=100, facecolor=COLORS["bg_panel"])
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels if scans else ['Veri Yok'], colors=colors, autopct='%1.1f%%' if scans else '', startangle=140, textprops={'color':"w"})
        fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)