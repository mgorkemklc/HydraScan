from django.db import models
from django.contrib.auth.models import User # Kullanıcıları da bağlayabiliriz

class Scan(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Beklemede'),
        ('RUNNING', 'Çalışıyor'),
        ('REPORTING', 'Rapor Oluşturuluyor'),
        ('COMPLETED', 'Tamamlandı'),
        ('FAILED', 'Hata'),
        ('CANCELLED', 'İptal Edildi'),
    ]

    # main.py'deki 'domain_input' (örn: localhost:3000)
    target_full_domain = models.CharField(max_length=255) 
    
    # main.py'deki 'internal_ip_range'
    internal_ip_range = models.CharField(max_length=100, blank=True, null=True)
    
    # main.py'deki 'aws_keys'
    aws_access_key = models.CharField(max_length=255, blank=True, null=True)
    aws_secret_key = models.CharField(max_length=255, blank=True, null=True)
    aws_region = models.CharField(max_length=100, blank=True, null=True)
    
    # main.py'deki 'apk_file_path'
    # NOT: Bu artık bir dosya yolu değil, S3'ye yüklenen dosyanın yolu olacak
    apk_file_s3_path = models.CharField(max_length=1024, blank=True, null=True)

    # main.py'deki 'api_key' (DİKKAT: Bunu kullanıcıya bağlamak daha güvenli)

    celery_task_id = models.CharField(max_length=50, blank=True, null=True)

    # İşin durumunu takip etmek için
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    
    # main.py'deki 'output_dir' (Artık /media/scan_outputs/123/ gibi olacak)
    output_directory = models.CharField(max_length=1024, blank=True)
    
    # report_module tarafından oluşturulan raporun yolu
    report_file_path = models.CharField(max_length=1024, blank=True, null=True)
    
    # Diğer bilgiler
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) # Kullanıcı sistemi ekleyince

    def __str__(self):
        # Modelin yönetim panelinde daha güzel görünmesi için bunu güncelleyelim
        return f"{self.target_full_domain} (Kullanıcı: {self.user.username})"