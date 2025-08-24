import os
from docker_helper import run_command_in_docker

def run_cloud_tests(aws_access_key, aws_secret_key, aws_region, output_dir, image_name):
    """
    AWS ortamında güvenlik denetimleri gerçekleştirir.

    Args:
        aws_access_key (str): AWS Access Key ID.
        aws_secret_key (str): AWS Secret Access Key.
        aws_region (str): Hedef AWS bölgesi (örn: "us-east-1").
        output_dir (str): Çıktıların kaydedileceği dizin.
        image_name (str): Kullanılacak Docker imajı.
    """
    print("\n[+] Bulut Ortamı (AWS) Testleri modülü başlatılıyor...")

    # API anahtarlarını Docker'a environment variable olarak aktarmak için argüman listesi
    docker_env_args = [
        '-e', f'AWS_ACCESS_KEY_ID={aws_access_key}',
        '-e', f'AWS_SECRET_ACCESS_KEY={aws_secret_key}',
        '-e', f'AWS_DEFAULT_REGION={aws_region}'
    ]

    # AWS üzerinde çalıştırılacak komutlar
    commands = {
        # 1. Adım: Anahtarların çalışıp çalışmadığını ve kimliğimizi kontrol et
        "aws_caller_identity_ciktisi.txt": "aws sts get-caller-identity",

        # 2. Adım: Hesaptaki tüm S3 bucket'larını listele (yaygın bir bilgi sızıntısı kaynağı)
        "aws_s3_buckets_ciktisi.txt": "aws s3 ls",

        # 3. Adım: Prowler ile tüm AWS hesabını CIS benchmark'larına göre denetle
        # Bu komutun çalışması uzun sürebilir.
        "prowler_aws_audit_ciktisi.txt": "prowler aws --cis"
    }

    # Her bir komutu, AWS kimlik bilgileriyle birlikte sırayla çalıştır
    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=docker_env_args)

    print("\n[+] Bulut Ortamı (AWS) Testleri modülü tamamlandı.")