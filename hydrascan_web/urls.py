# hydrascan_web/urls.py
from django.contrib import admin
from django.urls import path, include  # <-- 'include' fonksiyonunu import et

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),  # <-- BU SATIRI EKLE
]

# --- Tarama dosyalarını (media) sunmak için bunu ekle ---
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)