import customtkinter as ctk
import os
import json
from tkinter import messagebox
from ui.theme import COLORS

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, app_instance):
        super().__init__(parent, fg_color="transparent")
        self.app = app_instance
        
        cont = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=12)
        cont.pack(fill="both", expand=True, padx=50, pady=20)
        
        ctk.CTkLabel(cont, text="Uygulama Ayarları", font=("Roboto", 24, "bold"), text_color="white").pack(anchor="w", padx=40, pady=(40, 20))
        
        # API Key Alanı
        ctk.CTkLabel(cont, text="Gemini API Anahtarı (gemini-3-pro için)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(10, 5))
        self.set_api = ctk.CTkEntry(cont, placeholder_text="AIzaSy...", width=500, height=45, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.set_api.pack(anchor="w", padx=40, pady=(0, 20))
        
        if "api_key" in self.app.config: 
            self.set_api.insert(0, self.app.config["api_key"])
        
        # Webhook Alanı
        ctk.CTkLabel(cont, text="Bildirim Webhook (Discord/Slack vb.)", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(10, 5))
        self.set_webhook = ctk.CTkEntry(cont, placeholder_text="https://discord.com/api/webhooks/...", width=500, height=45, fg_color=COLORS["bg_main"], border_color=COLORS["border"], text_color="white")
        self.set_webhook.pack(anchor="w", padx=40, pady=5)
        
        if self.app.config.get("webhook_url"): 
            self.set_webhook.insert(0, self.app.config["webhook_url"])
        
        # Tema Ayarı
        ctk.CTkLabel(cont, text="Tema", font=("Roboto", 14, "bold"), text_color=COLORS["accent"]).pack(anchor="w", padx=40, pady=(15, 5))
        self.theme_switch = ctk.CTkSwitch(cont, text="Aydınlık Mod (Önerilmez)", command=self.toggle_theme, progress_color=COLORS["accent"])
        self.theme_switch.pack(anchor="w", padx=40)
        
        if self.app.config.get("theme") == "Light": 
            self.theme_switch.select()

        # Kaydet Butonu
        ctk.CTkButton(cont, text="💾 Ayarları Kaydet", width=200, height=45, font=("Roboto", 14, "bold"), fg_color=COLORS["success"], hover_color="#16a34a", command=self.save_settings).pack(anchor="w", padx=40, pady=(30, 40))

    def toggle_theme(self):
        mode = "Light" if self.theme_switch.get() else "Dark"
        ctk.set_appearance_mode(mode)
        self.app.config["theme"] = mode
        self.app.save_config()
        
    def save_settings(self):
        self.app.config["api_key"] = self.set_api.get()
        self.app.config["webhook_url"] = self.set_webhook.get()
        self.app.save_config()
        messagebox.showinfo("Başarılı", "Ayarlar başarıyla kaydedildi!")