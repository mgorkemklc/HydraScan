# ui/components.py
import customtkinter as ctk
from ui.theme import COLORS

class MetricCard(ctk.CTkFrame):
    def __init__(self, parent, title, value, sub_text, icon, icon_color):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=15, border_width=1, border_color=COLORS["border"])
        self.grid_columnconfigure(1, weight=1)

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=0, sticky="w", padx=20, pady=20)

        ctk.CTkLabel(text_frame, text=title, font=("Roboto", 14), text_color=COLORS["text_gray"]).pack(anchor="w")
        self.lbl_value = ctk.CTkLabel(text_frame, text=value, font=("Roboto", 36, "bold"), text_color="white")
        self.lbl_value.pack(anchor="w", pady=(5, 5))
        ctk.CTkLabel(text_frame, text=sub_text, font=("Roboto", 12), text_color=icon_color).pack(anchor="w")

        self.icon_frame = ctk.CTkFrame(self, width=54, height=54, corner_radius=27, fg_color=COLORS["bg_input"])
        self.icon_frame.grid(row=0, column=2, padx=20, pady=20, sticky="e")
        self.icon_frame.pack_propagate(False) 
        ctk.CTkLabel(self.icon_frame, text=icon, font=("Arial", 24), text_color=icon_color).place(relx=0.5, rely=0.5, anchor="center")

class ScanOptionCard(ctk.CTkFrame):
    def __init__(self, parent, title, description, icon, value, variable):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=12, border_width=2, border_color=COLORS["bg_panel"])
        self.value = value
        self.variable = variable
        self.bind("<Button-1>", self.select)
        
        self.lbl_icon = ctk.CTkLabel(self, text=icon, font=("Arial", 32), text_color=COLORS["accent"])
        self.lbl_icon.pack(pady=(20, 10))
        self.lbl_icon.bind("<Button-1>", self.select)
        
        self.lbl_title = ctk.CTkLabel(self, text=title, font=("Roboto", 16, "bold"), text_color="white")
        self.lbl_title.pack(pady=(0, 5))
        self.lbl_title.bind("<Button-1>", self.select)
        
        self.lbl_desc = ctk.CTkLabel(self, text=description, font=("Roboto", 11), text_color=COLORS["text_gray"], wraplength=180)
        self.lbl_desc.pack(pady=(0, 20), padx=10)
        self.lbl_desc.bind("<Button-1>", self.select)
        
        if self.variable: 
            self.variable.trace_add("write", self.update_state)

    def select(self, event=None):
        if self.variable: self.variable.set(self.value)

    def update_state(self, *args):
        if self.variable.get() == self.value:
            self.configure(border_color=COLORS["accent"], fg_color=COLORS["bg_input"])
        else:
            self.configure(border_color=COLORS["bg_panel"], fg_color=COLORS["bg_panel"])