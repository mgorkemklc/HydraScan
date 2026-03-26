import os
import io
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import matplotlib.pyplot as plt

def parse_findings(output_dir):
    # Basit bir parser: Çıktı dosyalarındaki zafiyet seviyelerini sayar
    severity_counts = {"Kritik": 0, "Yüksek": 0, "Orta": 0, "Düşük/Bilgi": 0}
    findings = []

    nuclei_file = os.path.join(output_dir, "nuclei_ciktisi.txt")
    if os.path.exists(nuclei_file):
        with open(nuclei_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if "[critical]" in line.lower(): severity_counts["Kritik"] += 1; findings.append(line.strip())
                elif "[high]" in line.lower(): severity_counts["Yüksek"] += 1; findings.append(line.strip())
                elif "[medium]" in line.lower(): severity_counts["Orta"] += 1; findings.append(line.strip())
                elif "[low]" in line.lower() or "[info]" in line.lower(): severity_counts["Düşük/Bilgi"] += 1

    return severity_counts, findings

def generate_pie_chart(severity_counts):
    labels = list(severity_counts.keys())
    sizes = list(severity_counts.values())
    colors_list = ['#ff0000', '#ff9900', '#ffff00', '#33cc33'] # Kırmızı, Turuncu, Sarı, Yeşil
    
    # Eğer hiç zafiyet yoksa boş grafik çizmesin
    if sum(sizes) == 0:
        sizes = [1]; labels = ["Zafiyet Bulunamadı"]; colors_list = ['#cccccc']

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=140)
    ax.axis('equal')
    
    img_data = io.BytesBytesIO() if hasattr(io, 'BytesIO') else io.BytesIO()
    plt.savefig(img_data, format='png', bbox_inches='tight')
    plt.close(fig)
    img_data.seek(0)
    return img_data

def generate_pdf_report(scan_id, target, output_dir):
    report_path = os.path.join(output_dir, f"HydraScan_Report_ID{scan_id}.pdf")
    
    severity_counts, findings = parse_findings(output_dir)
    chart_data = generate_pie_chart(severity_counts)

    doc = SimpleDocTemplate(report_path, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # Özel Stiller
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=24, alignment=1, spaceAfter=20)
    h2_style = ParagraphStyle(name='H2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, spaceAfter=10, textColor=colors.HexColor("#1e293b"))
    normal_style = styles['Normal']

    story = []
    
    # Başlık ve Meta Bilgiler
    story.append(Paragraph("Sızma Testi Raporu", title_style))
    story.append(Paragraph("<b>HydraScan Kurumsal Güvenlik Platformu</b>", ParagraphStyle(name='C', alignment=1, fontSize=12, spaceAfter=30)))
    
    data = [
        ["Tarama ID:", str(scan_id)],
        ["Hedef:", target],
        ["Tarih:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Durum:", "Tamamlandı"]
    ]
    t = Table(data, colWidths=[100, 300])
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    story.append(t)
    story.append(Spacer(1, 30))

    # Yönetici Özeti ve Grafik
    story.append(Paragraph("Yönetici Özeti (Zafiyet Dağılımı)", h2_style))
    story.append(RLImage(chart_data, width=400, height=250))
    story.append(Spacer(1, 20))

    # Tespit Edilen Kritik Bulgular
    story.append(Paragraph("Öne Çıkan Bulgular (Nuclei)", h2_style))
    if findings:
        for finding in findings[:15]: # İlk 15 bulguyu rapora ekle
            story.append(Paragraph(f"• {finding}", normal_style))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("Kritik veya Yüksek seviyeli doğrudan sömürülebilir zafiyet tespit edilemedi.", normal_style))

    doc.build(story)
    return report_path