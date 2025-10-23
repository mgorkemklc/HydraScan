# Dockerfile
# 1. Temel İmaj: Python 3.11'in hafif bir versiyonu
FROM python:3.11-slim

# 2. Sistem Bağımlılıkları Kurulumu
#    - build-essential ve libpq-dev: psycopg2'nin (PostgreSQL) derlenmesi için gerekli
#    - curl: Sağlık kontrolleri için (isteğe bağlı ama faydalı)
RUN apt-get update \
    && apt-get install -y build-essential libpq-dev curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Ortam Değişkenleri
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 4. Çalışma Dizinini Oluştur
WORKDIR /app

# 5. Gereksinimleri Yükle
#    Önce sadece requirements.txt'yi kopyala ve yükle
#    Bu sayede kod değişse bile kütüphaneler cache'lenir, build hızlanır
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Tüm Proje Kodunu Kopyala
COPY . .

# 7. Statik Dosyaları Topla (S3 için)
#    settings.py'nin S3'ü kullanacağını varsayıyoruz (Aşama 1'de yaptık)
#    Bu komut AWS_STORAGE_BUCKET_NAME'e bağlanmaya çalışabilir.
#    Secrets Manager'a erişim gerektirebilir. Build sırasında hata alırsak
#    bu adımı bir script'e taşıyabiliriz.
# RUN python manage.py collectstatic --noinput

# Not: CMD veya ENTRYPOINT tanımlamıyoruz.
# Hangi komutun (gunicorn, celery worker, migrate) çalışacağını
# AWS ECS Görev Tanımı'nda (Task Definition) belirleyeceğiz.