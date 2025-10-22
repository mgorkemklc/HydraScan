import os
from celery import Celery

# 'celery' programı için varsayılan Django ayar modülünü ayarla.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hydrascan_web.settings')

# 'hydrascan_web' projesi için bir Celery uygulaması oluştur
app = Celery('hydrascan_web')

# Django ayarlarından yapılandırmayı yükle (namespace='CELERY' tüm ayarların CELERY_ ile başlaması gerektiğini söyler)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django app'lerindeki tüm görevleri (tasks.py) otomatik olarak bul
app.autodiscover_tasks()