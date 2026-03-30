import customtkinter as ctk
from tkinter import ttk
from ui.theme import COLORS
import database

class ReportsView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance

        # Üst Kısım: Başlık ve Arama Filtresi
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(top_frame, text="Rapor Arşivi & Uyumluluk", font=("Roboto", 24, "bold"), text_color="white").pack(side="left")

        filter_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], height=60, corner_radius=10)
        filter_bar.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(filter_bar, text="Arşiv Filtrele:", font=("Roboto", 13), text_color=COLORS["text_gray"]).pack(side="left", padx=20)
        self.entry_search = ctk.CTkEntry(filter_bar, placeholder_text="Domain veya Rapor ID ara...", width=300, fg_color=COLORS["bg_input"], border_color=COLORS["border"], text_color="white")
        self.entry_search.pack(side="left", padx=10, pady=15)
        
        ctk.CTkButton(filter_bar, text="Ara / Yenile", width=120, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="white", font=("Roboto", 12, "bold"), command=self.refresh_reports_list).pack(side="left")

        # Treeview (Rapor Listesi) Alanı
        list_container = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=12)
        list_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.tree = self.create_treeview(list_container)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)

        # Alt Butonlar (PDF, Karşılaştır, Sil)
        btn_frm = ctk.CTkFrame(self, fg_color="transparent")
        btn_frm.pack(fill="x", padx=20, pady=(0, 20))

        # Senin istediğin ISO 27001 PDF butonu hazırlığı
        ctk.CTkButton(btn_frm, text="📄 PDF İndir (ISO 27001)", height=35, fg_color=COLORS["success"], hover_color="#16a34a", font=("Roboto", 13, "bold")).pack(side="left", padx=(0, 10))
        
        # Re-Test / Karşılaştırma Butonu
        ctk.CTkButton(btn_frm, text="⚖️ Karşılaştır (Re-Test)", height=35, fg_color=COLORS["warning"], hover_color="#d97706", text_color="black", font=("Roboto", 13, "bold")).pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frm, text="🗑️ Seçili Taramayı Sil", height=35, fg_color=COLORS["danger"], hover_color="#dc2626", font=("Roboto", 13, "bold")).pack(side="right")

    def create_treeview(self, parent):
        # Tkinter'ın klasik çirkin tablosunu, koyu temamıza uyduruyoruz
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=COLORS["bg_main"], foreground="white", fieldbackground=COLORS["bg_main"], borderwidth=0, rowheight=45, font=("Roboto", 11))
        style.configure("Treeview.Heading", background=COLORS["bg_panel"], foreground=COLORS["text_gray"], borderwidth=0, font=("Roboto", 12, "bold"))
        style.map("Treeview", background=[('selected', COLORS["accent"])])

        tree = ttk.Treeview(parent, columns=("ID", "Target", "Status", "Date"), show="headings", style="Treeview")
        tree.heading("ID", text=" ID")
        tree.column("ID", width=60, anchor="center")
        tree.heading("Target", text=" HEDEF BİLGİSİ")
        tree.column("Target", width=350)
        tree.heading("Status", text=" DURUM")
        tree.column("Status", width=150)
        tree.heading("Date", text=" TARİH")
        tree.column("Date", width=150, anchor="center")
        return tree

    def refresh_reports_list(self):
        print("[*] Rapor listesi veritabanından çekiliyor...")
        import database
        
        search_query = self.entry_search.get().lower()
        
        # HATA BURADAYDI: Doğrudan current_user sözlüğünü veriyorduk.
        # ÇÖZÜM: Sadece ID numarasını (integer) alıyoruz.
        user_id = self.app.current_user.get('id') if self.app.current_user else None
        
        try:
            scans = database.get_all_scans(user_id)
            
            # Tabloyu temizle
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Verileri tabloya ekle
            for scan in scans:
                if search_query and search_query not in scan['target_full_domain'].lower(): 
                    continue
                self.insert_scan_to_tree(scan)
        except Exception as e:
            print(f"[-] Veritabanı çekilirken hata oluştu: {e}")

    def insert_scan_to_tree(self, scan):
        import datetime
        st = scan['status']
        icon = "⏳" if st == "PENDING" else "⚡" if st == "RUNNING" else "✅" if st == "COMPLETED" else "❌"
        
        d = scan['created_at']
        if isinstance(d, str): 
            d = d[:16]
        elif isinstance(d, datetime.datetime): 
            d = d.strftime("%Y-%m-%d %H:%M")
            
        self.tree.insert("", "end", iid=scan['id'], values=(scan['id'], scan['target_full_domain'], f"{icon} {st}", d))