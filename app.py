import sys
import os
import threading
import concurrent.futures
import time

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame, QLineEdit, QComboBox, 
                             QGraphicsDropShadowEffect, QGridLayout, QTextEdit, QMessageBox)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRectF, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

# --- ARKA PLAN MODÜLLERİ ---
import database
from core import recon_module, web_app_module, mobile_module, report_module, internal_network_module

# =========================================================
# THREAD-SAFE İLETİŞİM (C++ Sinyal Motoru)
# Arka plandaki taramanın arayüzü çökertmeden log yollaması için
# =========================================================
class WorkerSignals(QObject):
    log_msg = pyqtSignal(str)
    finished = pyqtSignal(int, str)

# =========================================================
# C++ QT STİL MOTORU
# =========================================================
DARK_THEME = """
    QMainWindow { background-color: #050810; }
    QLabel { color: #f9fafb; font-family: 'Segoe UI'; }
    
    QFrame#Sidebar { background-color: #0b0f19; border-right: 1px solid #1f2937; }
    
    QFrame#Card { 
        background-color: #0b0f19; 
        border-radius: 15px; 
        border: 1px solid #1f2937;
    }
    
    QLineEdit, QComboBox {
        background-color: #111827; color: white;
        border: 1px solid #374151; border-radius: 8px;
        padding: 10px; font-size: 14px;
    }
    QLineEdit:focus, QComboBox:focus { border: 1px solid #6366f1; background-color: #1f2937; }
    
    QPushButton#NeonBtn {
        background-color: #4f46e5; color: white;
        font-weight: bold; border-radius: 8px; padding: 10px 25px; font-size: 14px;
    }
    QPushButton#NeonBtn:hover { background-color: #4338ca; border: 1px solid #818cf8; }
    
    QPushButton#MenuBtn {
        text-align: left; padding: 12px 15px; color: #9ca3af; 
        background: transparent; font-size: 15px; border-radius: 8px; font-weight: bold;
    }
    QPushButton#MenuBtn:hover { background-color: rgba(99, 102, 241, 0.1); color: #818cf8; }
    
    QPushButton#ToggleBtn {
        background: transparent; color: #818cf8; font-size: 20px; border-radius: 5px;
    }
    QPushButton#ToggleBtn:hover { background-color: rgba(255, 255, 255, 0.05); }
    
    QTextEdit {
        background-color: #030712; color: #22d3ee; font-family: Consolas;
        border: 1px solid #1f2937; border-radius: 10px; padding: 10px;
    }
"""

class NeonRingChart(QWidget):
    def __init__(self, percentage, color_hex, title):
        super().__init__()
        self.percentage = percentage
        self.color = QColor(color_hex)
        self.title = title
        self.setFixedSize(160, 160)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(15, 15, 130, 130)
        thickness = 12

        pen_bg = QPen(QColor(31, 41, 55), thickness)
        painter.setPen(pen_bg)
        painter.drawEllipse(rect)

        pen_val = QPen(self.color, thickness, cap=Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_val)
        span_angle = int(-self.percentage * 3.6 * 16) 
        painter.drawArc(rect, 90 * 16, span_angle)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"%{self.percentage}")

        painter.setPen(QColor(156, 163, 175))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_rect = QRectF(0, 115, 160, 40)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.title)

    def update_value(self, new_val):
        self.percentage = new_val
        self.update() # Çizimi yeniler

# =========================================================
# ANA UYGULAMA PENCERESİ
# =========================================================
class HydraScanApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HydraScan Enterprise")
        self.setGeometry(100, 100, 1300, 850)
        self.setStyleSheet(DARK_THEME)

        # Veritabanı ve Kullanıcı Hazırlığı
        database.init_db()
        self.current_user = database.login_check("superadmin", "admin123")
        if not self.current_user:
            database.register_user("superadmin", "admin123", "Superadmin", 1)
            self.current_user = database.login_check("superadmin", "admin123")

        self.setup_ui()
        self.refresh_stats()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === SOL MENÜ ===
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 20, 15, 20)
        
        top_sidebar = QHBoxLayout()
        self.title_lbl = QLabel(" 🐉 HYDRASCAN")
        self.title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        
        self.toggle_btn = QPushButton("☰")
        self.toggle_btn.setObjectName("ToggleBtn")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        
        top_sidebar.addWidget(self.title_lbl)
        top_sidebar.addStretch()
        top_sidebar.addWidget(self.toggle_btn)
        self.sidebar_layout.addLayout(top_sidebar)
        self.sidebar_layout.addSpacing(30)
        
        self.btn_dashboard = self.create_menu_btn("📊  Genel Bakış", active=True)
        self.btn_reports = self.create_menu_btn("📄  Raporlar")
        self.btn_settings = self.create_menu_btn("⚙️  Ayarlar")
        
        self.sidebar_layout.addWidget(self.btn_dashboard)
        self.sidebar_layout.addWidget(self.btn_reports)
        self.sidebar_layout.addWidget(self.btn_settings)
        self.sidebar_layout.addStretch()
        
        self.profile_lbl = QLabel(f"{self.current_user['username'][:2].upper()} | {self.current_user['username'].upper()}\n{self.current_user['role']}")
        self.profile_lbl.setStyleSheet("color: #818cf8; font-weight: bold; font-size: 12px;")
        self.sidebar_layout.addWidget(self.profile_lbl)
        
        main_layout.addWidget(self.sidebar)

        # === ANA İÇERİK ===
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 30, 40, 30)

        # Header
        header_layout = QHBoxLayout()
        header_title = QLabel("Sistem İzleme Paneli")
        header_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        self.combo = QComboBox()
        self.combo.addItems(["web", "mobile", "network"])
        self.combo.setFixedWidth(120)
        header_layout.addWidget(self.combo)
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Hedef URL / IP / Dosya girin...")
        self.target_input.setFixedWidth(300)
        header_layout.addWidget(self.target_input)
        
        launch_btn = QPushButton("🚀 BAŞLAT")
        launch_btn.setObjectName("NeonBtn")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(99, 102, 241, 150))
        shadow.setOffset(0, 0)
        launch_btn.setGraphicsEffect(shadow)
        launch_btn.clicked.connect(self.trigger_scan)
        header_layout.addWidget(launch_btn)
        
        content_layout.addLayout(header_layout)
        content_layout.addSpacing(20)

        # Grafikler
        stats_layout = QGridLayout()
        stats_layout.setSpacing(25)
        
        chart_frame = QFrame()
        chart_frame.setObjectName("Card")
        chart_layout = QHBoxLayout(chart_frame)
        self.health_chart = NeonRingChart(100, "#10b981", "SİSTEM SAĞLIĞI")
        self.progress_chart = NeonRingChart(0, "#6366f1", "TARAMA İLERLEMESİ")
        chart_layout.addWidget(self.health_chart)
        chart_layout.addWidget(self.progress_chart)
        stats_layout.addWidget(chart_frame, 0, 0, 1, 2)
        
        self.card_active = self.create_info_card("Aktif Taramalar", "0 İşlem", "Çalışıyor", "#6366f1")
        self.card_total = self.create_info_card("Arşivdeki Tarama", "0 Adet", "Tamamlanmış", "#10b981")
        stats_layout.addWidget(self.card_active[0], 1, 0)
        stats_layout.addWidget(self.card_total[0], 1, 1)

        content_layout.addLayout(stats_layout)
        
        # Terminal (Ham Çıktı) Alanı
        content_layout.addSpacing(20)
        term_label = QLabel(">_ CANLI TERMİNAL")
        term_label.setStyleSheet("color: #4ade80; font-weight: bold;")
        content_layout.addWidget(term_label)
        
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setFixedHeight(200)
        content_layout.addWidget(self.terminal)

        main_layout.addWidget(content_area)

    def create_menu_btn(self, text, active=False):
        btn = QPushButton(text)
        btn.setObjectName("MenuBtn")
        if active:
            btn.setStyleSheet("background-color: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3);")
        return btn

    def create_info_card(self, title, value, subtext, color):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 25, 25, 25)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #9ca3af; font-size: 14px; font-weight: bold;")
        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        lbl_sub = QLabel(subtext)
        lbl_sub.setStyleSheet("color: #6b7280; font-size: 12px;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        layout.addWidget(lbl_sub)
        return card, lbl_val

    def toggle_sidebar(self):
        width = self.sidebar.width()
        new_width = 80 if width == 260 else 260
        if new_width == 80:
            self.title_lbl.hide()
            self.profile_lbl.hide()
            self.btn_dashboard.setText("📊")
            self.btn_reports.setText("📄")
            self.btn_settings.setText("⚙️")
        else:
            self.title_lbl.show()
            self.profile_lbl.show()
            self.btn_dashboard.setText("📊  Genel Bakış")
            self.btn_reports.setText("📄  Raporlar")
            self.btn_settings.setText("⚙️  Ayarlar")

        self.anim1 = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.anim1.setDuration(300)
        self.anim1.setStartValue(width)
        self.anim1.setEndValue(new_width)
        self.anim1.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.anim1.start()

    # ==================================================================
    # VERİTABANI VE İSTATİSTİK YENİLEME
    # ==================================================================
    def refresh_stats(self):
        scans = database.get_all_scans(self.current_user)
        total = len(scans)
        active = sum(1 for s in scans if s['status'] in ["RUNNING", "PENDING", "REPORTING"])
        
        self.card_total[1].setText(f"{total} Adet")
        self.card_active[1].setText(f"{active} İşlem")
        
        # Grafikleri Güncelle
        if active > 0: self.progress_chart.update_value(50)
        else: self.progress_chart.update_value(0)

    # ==================================================================
    # ARKA PLAN TARAMA MOTORU (ESKİ UYGULAMADAN TAŞINDI)
    # ==================================================================
    def trigger_scan(self):
        domain = self.target_input.text().strip()
        scan_type = self.combo.currentText()
        
        if not domain:
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen bir hedef girin!")
            return

        self.terminal.clear()
        self.terminal.append(f"[*] SİSTEM HAZIR. HEDEF: {domain} ({scan_type.upper()})")
        self.target_input.clear()

        # Veritabanı Kaydı
        scan_data = {
            "domain": domain, 
            "scan_type": scan_type,
            "apk_path": domain if scan_type == "mobile" else None,
            "gemini_key": "", # Ayarlardan çekilecek
            "wordlist": None
        }
        
        try:
            scan_id = database.create_scan(scan_data, self.current_user['id'], self.current_user['company_id'], self.current_user['id'])
            self.refresh_stats()
            
            # Sinyal Motorunu Başlat (Arka planın arayüze veri gönderebilmesi için)
            self.signals = WorkerSignals()
            self.signals.log_msg.connect(self.update_terminal)
            self.signals.finished.connect(self.scan_completed)

            # Tarama işlemini arka plan Thread'ine (İş parçacığına) gönder!
            threading.Thread(target=self.run_scan_logic_thread, args=(scan_id, scan_data, self.signals), daemon=True).start()

        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def update_terminal(self, msg):
        """Arka plandan gelen ham logları canlı canlı terminale yazar."""
        self.terminal.append(msg.strip())
        # Scrollu en alta kaydır
        self.terminal.verticalScrollBar().setValue(self.terminal.verticalScrollBar().maximum())

    def scan_completed(self, scan_id, status):
        """Tarama bittiğinde tetiklenir."""
        self.refresh_stats()
        QMessageBox.information(self, "İşlem Tamam", f"Tarama ID {scan_id} {status} olarak sonuçlandı.")
        self.progress_chart.update_value(100)

    # BU FONKSİYON ARKA PLANDA ÇALIŞIR, ARAYÜZÜ DONDURMAZ
    def run_scan_logic_thread(self, scan_id, data, signals):
        def log_cb(msg): 
            signals.log_msg.emit(msg)

        log_cb(f"[*] Tarama Motoru Başlatıldı ID: {scan_id} Modül: {data['scan_type']}")

        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            
            img = "pentest-araci-kali:v1.5"
            dom = data['domain']
            scan_type = data['scan_type']
            selected_tools = ["nmap", "gobuster", "nuclei", "whois"] # Varsayılan Web Araçları
            
            with concurrent.futures.ThreadPoolExecutor() as ex:
                futures = []
                if scan_type == "web":
                    futures.append(ex.submit(recon_module.run_reconnaissance, dom, out, img, selected_tools))
                    # stream_callback sayesinde loglar saniye saniye arayüze akar!
                    futures.append(ex.submit(web_app_module.run_web_tests, dom, out, img, selected_tools, stream_callback=log_cb, custom_wordlist=None))
                elif scan_type == "network":
                    futures.append(ex.submit(internal_network_module.run_network_tests, dom, out, img, selected_tools))
                elif scan_type == "mobile":
                    futures.append(ex.submit(mobile_module.run_mobile_tests, data['apk_path'], out, img, stream_callback=log_cb))

                for f in concurrent.futures.as_completed(futures):
                    try:
                        f.result()
                    except Exception as e:
                        log_cb(f"[-] Alt Modül Hatası: {str(e)}")

            log_cb("\n[*] AI Raporu hazırlanıyor...")
            database.update_scan_status(scan_id, 'REPORTING')
            
            # Eski modüldeki raporlama fonksiyonunu çağırıyoruz
            path = report_module.generate_report(out, dom, data['gemini_key'])
            
            status = "COMPLETED" if path else "FAILED"
            database.complete_scan(scan_id, path, status)
            
            log_cb(f"[+] Tarama Tamamlandı. Çıktı klasörü: {out}")
            signals.finished.emit(scan_id, status)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            log_cb(f"[-] Kritik Hata: {str(e)}\n{error_trace}")
            database.complete_scan(scan_id, None, "FAILED")
            signals.finished.emit(scan_id, "FAILED")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HydraScanApp()
    window.show()
    sys.exit(app.exec())