import os
import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import json
import database

import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt

def parse_findings(output_dir):
    severity_counts = {"Kritik": 0, "Yüksek": 0, "Orta": 0, "Düşük/Bilgi": 0}
    findings = []

    if not os.path.exists(output_dir):
        return severity_counts, findings

    for file in os.listdir(output_dir):
        if not file.endswith('.txt'): continue
        filepath = os.path.join(output_dir, file)
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Nuclei Zafiyetleri
            if "nuclei" in file:
                for line in lines:
                    lower_line = line.lower()
                    if "[critical]" in lower_line: 
                        severity_counts["Kritik"] += 1; findings.append(line.strip())
                    elif "[high]" in lower_line: 
                        severity_counts["Yüksek"] += 1; findings.append(line.strip())
                    elif "[medium]" in lower_line: 
                        severity_counts["Orta"] += 1; findings.append(line.strip())
                    elif "[low]" in lower_line or "[info]" in lower_line: 
                        severity_counts["Düşük/Bilgi"] += 1
                        
            # SQLMap Enjeksiyon Kontrolü
            elif "sqlmap" in file:
                if "is vulnerable" in content.lower() or "injectable" in content.lower():
                    severity_counts["Kritik"] += 1
                    findings.append("[SQLMAP] [critical] Hedef veritabanında SQL Injection tespit edildi!")
                    
            # Dalfox XSS Kontrolü
            elif "dalfox" in file:
                vulnerabilities = [line for line in lines if "vulnerable" in line.lower() or "poc" in line.lower()]
                if vulnerabilities:
                    severity_counts["Yüksek"] += len(vulnerabilities)
                    findings.append(f"[DALFOX] [high] {len(vulnerabilities)} adet DOM/Reflected XSS tespit edildi.")
                    
            # Nmap Açık Port Kontrolü
            elif "nmap" in file:
                open_ports = [line for line in lines if "open" in line and "tcp" in line]
                severity_counts["Düşük/Bilgi"] += len(open_ports)
                if open_ports:
                    findings.append(f"[NMAP] [info] Hedefte {len(open_ports)} adet açık TCP portu tespit edildi.")

    return severity_counts, findings

def parse_and_save_vulnerabilities(scan_id, output_dir):
    """Araçların JSON çıktılarını okur, CVSS skorlarını ve çözüm önerilerini DB'ye yazar."""
    nuclei_file = os.path.join(output_dir, "nuclei_ciktisi.json")
    
    if os.path.exists(nuclei_file):
        with open(nuclei_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    info = data.get('info', {})
                    
                    vuln_name = info.get('name', 'Bilinmeyen Zafiyet')
                    severity = info.get('severity', 'info').capitalize()
                    
                    # CVSS skorunu parse etme
                    cvss = info.get('classification', {}).get('cvss-score', 0.0)
                    
                    # Çözüm Önerisi (Remediation)
                    remediation = info.get('remediation', 'Spesifik bir çözüm önerisi sunulmamıştır. Lütfen yazılımınızı en güncel sürüme yükseltin.')
                    
                    # Kanıt (CURL formatında Request)
                    evidence = data.get('curl-command', 'Kanıt verisi oluşturulamadı.')
                    
                    # Sadece Medium ve üzeri zafiyetleri Re-test havuzuna alıyoruz
                    if severity in ['Critical', 'High', 'Medium', 'Kritik', 'Yüksek', 'Orta']:
                        database.add_vulnerability(scan_id, 'Nuclei', vuln_name, severity, cvss, evidence, remediation)
                except Exception as e:
                    continue

def generate_pie_chart(severity_counts):
    labels = list(severity_counts.keys())
    sizes = list(severity_counts.values())
    colors_list = ['#ff0000', '#ff9900', '#ffff00', '#33cc33'] 
    
    if sum(sizes) == 0:
        sizes = [1]; labels = ["Zafiyet Bulunamadı"]; colors_list = ['#cccccc']

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')
    
    img_data = io.BytesIO() 
    plt.savefig(img_data, format='png', bbox_inches='tight')
    plt.close(fig)
    img_data.seek(0)
    return img_data

def generate_pdf_report(scan_id, target, output_dir):
    report_path = os.path.join(output_dir, f"HydraScan_Report_ID{scan_id}.pdf")
    parse_and_save_vulnerabilities(scan_id, output_dir)
    severity_counts, findings = parse_findings(output_dir)
    chart_data = generate_pie_chart(severity_counts)

    doc = SimpleDocTemplate(report_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=24, alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle(name='H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, spaceAfter=10, textColor=colors.HexColor("#1e293b"))
    normal_style = styles['Normal']

    story = []
    story.append(Paragraph("Sızma Testi Raporu", title_style))
    story.append(Paragraph("<b>HydraScan Kurumsal Güvenlik Platformu</b>", ParagraphStyle(name='C', alignment=1, fontSize=12, spaceAfter=30)))
    
    data = [
        ["Tarama ID:", str(scan_id)], ["Hedef:", target],
        ["Tarih:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")], ["Durum:", "Tamamlandı"]
    ]
    t = Table(data, colWidths=[100, 300])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(t)
    story.append(Spacer(1, 30))

    story.append(Paragraph("Yönetici Özeti (Zafiyet Dağılımı)", h2_style))
    story.append(RLImage(chart_data, width=400, height=250))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Teknik Detaylar ve Bulgular", h2_style))
    if findings:
        for finding in findings[:20]:
            story.append(Paragraph(f"• {finding}", normal_style))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("Platform tarafından doğrudan sömürülebilir kritik bir zafiyet tespit edilemedi.", normal_style))

    doc.build(story)
    return report_path