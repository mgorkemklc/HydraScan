from django.db import models
from django.contrib.auth.models import User

class Scan(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Beklemede'),
        ('RUNNING', 'Çalışıyor'),
        ('REPORTING', 'Rapor Oluşturuluyor'),
        ('COMPLETED', 'Tamamlandı'),
        ('FAILED', 'Hata'),
        ('CANCELLED', 'İptal Edildi'),
    ]

    target_full_domain = models.CharField(max_length=255) 
    internal_ip_range = models.CharField(max_length=100, blank=True, null=True)
    
    # AWS KEYLERİ SİLİNDİ
    
    # APK dosyası artık yerel sunucuda bir yol olacak
    apk_file_path = models.CharField(max_length=1024, blank=True, null=True)

    celery_task_id = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Yerel çıktı klasörü yolu (Örn: /app/media/scan_outputs/scan_15/)
    output_directory = models.CharField(max_length=1024, blank=True)
    
    # Rapor dosyasının yerel yolu
    report_file_path = models.CharField(max_length=1024, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.target_full_domain} (Kullanıcı: {self.user.username})"