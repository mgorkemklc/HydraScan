from django.urls import path
from . import views

urlpatterns = [
    # views.py'deki 'start_scan_view' fonksiyonunu çalıştırır
    path('', views.start_scan_view, name='start_scan'), 
    
    # views.py'deki 'scan_detail_view' fonksiyonunu çalıştırır
    # <int:scan_id> kısmı, URL'deki sayıyı (örn: /scan/123) yakalar
    path('scan/<int:scan_id>/', views.scan_detail_view, name='scan_detail_page'),
]