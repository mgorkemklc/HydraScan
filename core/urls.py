from django.urls import path
from . import views

urlpatterns = [
    # Ana sayfa (/) artık dashboard'u gösterecek
    path('', views.dashboard_view, name='dashboard'), 
    
    # Yeni tarama formu /scan/new/ adresine taşındı
    path('scan/new/', views.start_scan_view, name='start_scan'), 
    
    # Detay sayfası aynı kaldı
    path('scan/<int:scan_id>/', views.scan_detail_view, name='scan_detail_page'),
]