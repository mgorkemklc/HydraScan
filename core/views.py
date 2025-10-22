from django.shortcuts import render, redirect
from .models import Scan
from .tasks import run_hydrascan_task # Henüz oluşturmadık, ama oluşturacağız

def start_scan_view(request):
    if request.method == 'POST':
        # 1. Web formundan verileri al (eski input() yerinde)
        domain_input = request.POST.get('domain_input')
        internal_ip = request.POST.get('internal_ip_range')
        aws_key = request.POST.get('aws_access_key')
        aws_secret = request.POST.get('aws_secret_key')
        aws_region = request.POST.get('aws_region')
        gemini_key = request.POST.get('gemini_api_key')
        # ... (apk dosyası yüklemeyi de eklemelisin) ...
        
        # 2. Veritabanına yeni bir Scan kaydı oluştur
        new_scan = Scan.objects.create(
            target_full_domain=domain_input,
            internal_ip_range=internal_ip,
            aws_access_key=aws_key,
            aws_secret_key=aws_secret,
            aws_region=aws_region,
            gemini_api_key=gemini_key,
            status='PENDING'
        )
        
        # 3. Ağır işi Celery'ye havale et
        # .delay() komutu sayesinde bu satır anında çalışır ve Django beklemez
        run_hydrascan_task.delay(new_scan.id)
        
        # 4. Kullanıcıyı "Tarama Başladı" sayfasına yönlendir
        return redirect('scan_detail_page', scan_id=new_scan.id)
        
    return render(request, 'core/start_scan_form.html')

def scan_detail_view(request, scan_id):
    scan = Scan.objects.get(id=scan_id)
    # Bu sayfa, taramanın durumunu (PENDING, RUNNING, COMPLETED) gösterir
    # ve bittiyse raporu gösterir.
    return render(request, 'core/scan_detail.html', {'scan': scan})