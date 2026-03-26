import flet as ft
import threading
import os
import concurrent.futures
import database
from core import recon_module, web_app_module, mobile_module, report_module, internal_network_module

def main(page: ft.Page):
    # --- PENCERE VE TEMA AYARLARI ---
    page.title = "HydraScan Enterprise"
    page.window.width = 1400
    page.window.height = 900
    page.bgcolor = "#050810"
    page.padding = 0
    page.theme_mode = ft.ThemeMode.DARK

    # --- VERİTABANI BAŞLATMA ---
    database.init_db()
    current_user = database.login_check("superadmin", "admin123")
    if not current_user:
        database.register_user("superadmin", "admin123", "Superadmin", 1)
        current_user = database.login_check("superadmin", "admin123")

    # ==========================================
    # ORTAK BİLEŞENLER
    # ==========================================
    terminal_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)
    
    def log_msg(msg):
        terminal_list.controls.append(ft.Text(msg, color="#22d3ee", font_family="Consolas", size=13))
        page.update()

    # ==========================================
    # GÖRÜNÜM 1: DASHBOARD
    # ==========================================
    val_total = ft.Text("0", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    val_active = ft.Text("0", size=36, weight=ft.FontWeight.BOLD, color="#818cf8")
    val_failed = ft.Text("0", size=36, weight=ft.FontWeight.BOLD, color="#ef4444")

    def refresh_stats():
        scans = database.get_all_scans(current_user)
        val_total.value = str(len(scans))
        val_active.value = str(sum(1 for s in scans if s['status'] in ["RUNNING", "PENDING", "REPORTING"]))
        val_failed.value = str(sum(1 for s in scans if s['status'] == "FAILED"))
        page.update()

    def create_card(title, value_control, accent_color, has_glow=False):
        shadow_color = f"#26{accent_color[1:]}" if has_glow else ft.Colors.TRANSPARENT
        # Flet 0.80+ uyumlu kenarlık kullanımı
        border_style = ft.Border(
            top=ft.BorderSide(1, accent_color if has_glow else "#1f2937"),
            right=ft.BorderSide(1, accent_color if has_glow else "#1f2937"),
            bottom=ft.BorderSide(1, accent_color if has_glow else "#1f2937"),
            left=ft.BorderSide(1, accent_color if has_glow else "#1f2937")
        )
        return ft.Container(
            content=ft.Column([ft.Text(title, color="#9ca3af", size=12, weight=ft.FontWeight.BOLD), value_control], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#111827", border_radius=12, padding=25, expand=True,
            border=border_style,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color=shadow_color, offset=ft.Offset(0,0)) if has_glow else None
        )

    dashboard_view = ft.Column([
        ft.Text("Genel Bakış", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Row([
            create_card("TOPLAM TARAMA", val_total, "#1f2937"), 
            create_card("AKTİF GÖREVLER", val_active, "#6366f1", has_glow=True), 
            create_card("BAŞARISIZ / RİSK", val_failed, "#1f2937")
        ], spacing=20),
        ft.Container(height=20),
        ft.Container(
            expand=True, bgcolor="#030712", border_radius=12, 
            border=ft.Border(
                top=ft.BorderSide(1, "#1f2937"), right=ft.BorderSide(1, "#1f2937"),
                bottom=ft.BorderSide(1, "#1f2937"), left=ft.BorderSide(1, "#1f2937")
            ), 
            padding=20, 
            content=ft.Column([ft.Text(">_ CANLI TERMİNAL", color="#4ade80", weight=ft.FontWeight.BOLD), terminal_list])
        )
    ], expand=True, visible=True)

    # ==========================================
    # GÖRÜNÜM 2: YENİ TARAMA
    # ==========================================
    target_input = ft.TextField(hint_text="Hedef URL veya IP...", bgcolor="#1f2937", border_color="#374151", color=ft.Colors.WHITE, border_radius=8, expand=True)
    api_key_input = ft.TextField(hint_text="Gemini API Key...", bgcolor="#1f2937", border_color="#374151", color=ft.Colors.WHITE, border_radius=8, expand=True)
    
    selected_apk_path = [None]
    apk_path_text = ft.Text("Seçilen Dosya: Yok", color="#9ca3af")
    
    def pick_apk_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_apk_path[0] = e.files[0].path
            apk_path_text.value = f"Seçilen Dosya: {e.files[0].name}"
            page.update()

    # Flet 0.80+ FilePicker düzeltmesi
    apk_picker = ft.FilePicker()
    apk_picker.on_result = pick_apk_result
    page.overlay.append(apk_picker)

    tools = {"whois": True, "dig": True, "nmap": True, "subfinder": True, "amass": False, "nuclei": True, "gobuster": True, "sqlmap": False, "dalfox": False, "commix": False, "wapiti": False, "hydra": False, "mobile": False}
    checkboxes = {k: ft.Checkbox(label=k.title(), value=v, fill_color="#6366f1") for k, v in tools.items()}

    def start_scan_action(e):
        domain = target_input.value.strip()
        key = api_key_input.value.strip()
        selected_tools = [k for k, cb in checkboxes.items() if cb.value]
        
        if not domain:
            return log_msg("[-] HATA: Domain boş bırakılamaz.")
        if "mobile" in selected_tools and not selected_apk_path[0]:
            return log_msg("[-] HATA: Mobil analiz için APK seçmelisiniz.")

        log_msg(f"[*] Tarama Başlatılıyor: {domain}")
        scan_data = {"domain": domain, "gemini_key": key, "apk_path": selected_apk_path[0], "wordlist": None, "scan_type": "web"}
        if "mobile" in selected_tools: scan_data["scan_type"] = "mobile"
        
        try:
            scan_id = database.create_scan(scan_data, current_user['id'], current_user['company_id'], current_user['id'])
            refresh_stats()
            switch_view("Dashboard")
            threading.Thread(target=run_scan_thread, args=(scan_id, domain, selected_tools, scan_data), daemon=True).start()
        except Exception as ex:
            log_msg(f"[-] Veritabanı Hatası: {str(ex)}")

    def run_scan_thread(scan_id, dom, selected_tools, data):
        try:
            database.update_scan_status(scan_id, 'RUNNING')
            out = os.path.abspath(f"scan_outputs/scan_{scan_id}")
            if not os.path.exists(out): os.makedirs(out)
            database.set_scan_output_directory(scan_id, out)
            img = "pentest-araci-kali:v1.5"

            with concurrent.futures.ThreadPoolExecutor() as ex:
                futures = []
                futures.append(ex.submit(recon_module.run_reconnaissance, dom, out, img, selected_tools))
                futures.append(ex.submit(web_app_module.run_web_tests, dom, out, img, selected_tools, stream_callback=log_msg, custom_wordlist=None))
                
                if "mobile" in selected_tools and data['apk_path']:
                    futures.append(ex.submit(mobile_module.run_mobile_tests, data['apk_path'], out, img, stream_callback=log_msg))

                for f in concurrent.futures.as_completed(futures):
                    try: f.result()
                    except Exception as e: log_msg(f"[-] Modül Hatası: {str(e)}")

            log_msg("[*] AI Raporu hazırlanıyor...")
            database.update_scan_status(scan_id, 'REPORTING')
            path = report_module.generate_report(out, dom, data['gemini_key'])
            status = "COMPLETED" if path else "FAILED"
            database.complete_scan(scan_id, path, status)
            log_msg(f"[+] Tarama Bitti: {status}")
            refresh_stats()
        except Exception as e:
            log_msg(f"[-] Kritik Hata: {str(e)}")
            database.complete_scan(scan_id, None, "FAILED")
            refresh_stats()

    cb_items = list(checkboxes.values())
    cb_rows = [ft.Row(cb_items[i:i+4]) for i in range(0, len(cb_items), 4)]
    
    border_style = ft.Border(
        top=ft.BorderSide(1, "#1f2937"), right=ft.BorderSide(1, "#1f2937"),
        bottom=ft.BorderSide(1, "#1f2937"), left=ft.BorderSide(1, "#1f2937")
    )

    scan_view = ft.Column([
        ft.Text("Yeni Tarama Yapılandırması", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(bgcolor="#111827", padding=20, border_radius=12, border=border_style, content=ft.Column([
            ft.Text("Hedef ve API", color="#6366f1", weight=ft.FontWeight.BOLD),
            ft.Row([target_input, api_key_input]),
        ])),
        ft.Container(bgcolor="#111827", padding=20, border_radius=12, border=border_style, content=ft.Column([
            ft.Text("Araç Seçimi", color="#6366f1", weight=ft.FontWeight.BOLD),
            *cb_rows
        ])),
        ft.Container(bgcolor="#111827", padding=20, border_radius=12, border=border_style, content=ft.Row([
            ft.Text("Mobil Analiz (APK):", color="#6366f1", weight=ft.FontWeight.BOLD),
            ft.ElevatedButton("Dosya Yükle", on_click=lambda _: apk_picker.pick_files(allow_multiple=False), bgcolor="#1f2937", color=ft.Colors.WHITE),
            apk_path_text
        ])),
        ft.Container(height=10),
        ft.ElevatedButton("🚀 TARAMAYI BAŞLAT", bgcolor="#10b981", color=ft.Colors.WHITE, height=50, width=float('inf'), on_click=start_scan_action)
    ], expand=True, visible=False, scroll=ft.ScrollMode.AUTO)

    # ==========================================
    # YÖNLENDİRME VE SOL MENÜ
    # ==========================================
    content_area = ft.Container(content=ft.Stack([dashboard_view, scan_view]), expand=True, padding=40)

    def switch_view(view_name):
        dashboard_view.visible = (view_name == "Dashboard")
        scan_view.visible = (view_name == "Scan")
        page.update()

    def create_menu_btn(icon, text, view_name):
        return ft.Container(
            content=ft.Row([ft.Text(icon, size=18), ft.Text(text, color="#9ca3af", weight=ft.FontWeight.BOLD)]),
            padding=15, border_radius=8, ink=True,
            on_click=lambda e: switch_view(view_name)
        )

    sidebar = ft.Container(
        width=260, bgcolor="#0b0f19", padding=20,
        border=ft.Border(right=ft.BorderSide(1, "#1f2937")),
        content=ft.Column([
            ft.Text("🐉 HYDRASCAN", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Container(height=30),
            create_menu_btn("📊", "Genel Bakış", "Dashboard"),
            create_menu_btn("⌖", "Yeni Tarama", "Scan"),
            ft.Container(expand=True),
            ft.Text(f"{current_user['username'].upper()}\n{current_user['role']}", color="#818cf8", weight=ft.FontWeight.BOLD)
        ])
    )

    page.add(ft.Row([sidebar, content_area], expand=True, spacing=0))
    refresh_stats()
    log_msg("[*] Flet Motoru Başlatıldı. Tüm Araçlar ve İşlevsellik Aktif.")

if __name__ == '__main__':
    ft.run(main)