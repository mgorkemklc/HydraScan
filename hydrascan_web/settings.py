# hydrascan_web/settings.py (YENİ İÇERİK)

import os
import boto3
import json
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- AWS Secrets Manager'dan Ayarları Çekme ---
# Projenin tüm gizli bilgileri AWS'den çekilecek.
SECRET_NAME = "hydrascan/production"
REGION_NAME = "eu-central-1"  # <-- BURAYI GÜNCELLE (örn: eu-west-1, us-east-1)

# AWS SDK'yı (boto3) kullanarak Secrets Manager'a bağlan
session = boto3.session.Session()
client = session.client(service_name='secretsmanager', region_name=REGION_NAME)

try:
    get_secret_value_response = client.get_secret_value(SecretId=SECRET_NAME)
    # Gizli bilgileri JSON olarak al ve "secrets" adında bir değişkene ata
    secrets = json.loads(get_secret_value_response['String'])
except Exception as e:
    # Eğer gizli bilgilere ulaşılamazsa, uygulamanın çökmesi gerekir
    raise Exception(f"AWS Secrets Manager'dan '{SECRET_NAME}' çekilirken hata oluştu: {e}")

# --- Gizli Bilgileri Ayarlara Ata ---
SECRET_KEY = secrets['DJANGO_SECRET_KEY']
GEMINI_API_KEY = secrets['GEMINI_API_KEY']  # Gemini anahtarı artık buradan geliyor

# Production (Üretim) ayarı: DEBUG her zaman False olmalı
DEBUG = False

# ALLOWED_HOSTS'u doldur (ALB DNS'i ve alan adın buraya gelecek)
# '*' koymak ECS sağlık kontrollerinin çalışmasını sağlar
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'storages',  # django-storages'ı ekle
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hydrascan_web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hydrascan_web.wsgi.application'

# Database
# Veritabanı bilgileri artık db.sqlite3 değil, Secrets Manager'dan geliyor.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': secrets['DB_NAME'],
        'USER': secrets['DB_USER'],
        'PASSWORD': secrets['DB_PASSWORD'],
        'HOST': secrets['DB_HOST'],
        'PORT': '5432',  # PostgreSQL varsayılan portu
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CELERY AYARLARI (AWS REDIS İLE GÜNCELLENDİ) ---
# 'localhost' yerine Secrets Manager'dan çektiğimiz REDIS_HOST'u kullanıyoruz
CELERY_BROKER_URL = f"redis://{secrets['REDIS_HOST']}:6379/0"
CELERY_RESULT_BACKEND = f"redis://{secrets['REDIS_HOST']}:6379/0"

# --- AWS S3 AYARLARI (GÜNCELLENDİ) ---
# Kodu S3'e taşıyoruz. Statik dosyalar (admin CSS/JS) ve Media dosyaları (raporlar) S3'te saklanacak.
# AWS_ACCESS_KEY_ID ve AWS_SECRET_ACCESS_KEY'i siliyoruz.
# Boto3, ECS üzerinde IAM Rolü'nü (HydraScanAppECSRole) otomatik olarak kullanacak.
AWS_STORAGE_BUCKET_NAME = secrets.get('AWS_STORAGE_BUCKET_NAME', 'hydrascan-reports-bucket') # Secrets'tan oku veya varsayılanı kullan
AWS_S3_REGION_NAME = REGION_NAME
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Static files (CSS, JavaScript, Images) için S3 ayarları
STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Media files (Tarama Raporları) için S3 ayarları
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Static dosyaların S3'te bulunacağı klasör (collectstatic için)
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")