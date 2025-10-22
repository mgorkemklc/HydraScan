import os
import logging
from .docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 'output_dir' parametresi S3 argümanlarıyla değişti
def run_cloud_tests(access_key, secret_key, region, image_name, s3_client, bucket_name, s3_prefix):
    """
    Bulut (AWS) ortamı test araçlarını çalıştırır ve çıktıları S3'e yükler.
    """
    logging.info("\n[+] 6. Bulut Ortamı (AWS) Zafiyet Analizi modülü başlatılıyor...")

    # Docker konteynerine AWS anahtarlarını güvenli bir şekilde environment variable olarak geçir
    extra_docker_args = [
        "-e", f"AWS_ACCESS_KEY_ID={access_key}",
        "-e", f"AWS_SECRET_ACCESS_KEY={secret_key}",
        "-e", f"AWS_DEFAULT_REGION={region}"
    ]

    commands = {
        "aws_s3_ls_ciktisi.txt": "aws s3 ls",
        "aws_iam_list_users_ciktisi.txt": "aws iam list-users",
        "aws_ec2_describe_instances_ciktisi.txt": "aws ec2 describe-instances"
    }

    for output_filename, command in commands.items():
        # DEĞİŞİKLİK: Artık yerel yol değil, S3 anahtarı (yolu) oluşturuyoruz
        s3_key = f"{s3_prefix}{output_filename}"
        
        # docker_helper'a S3 bilgilerini VE extra_docker_args'ı iletiyoruz
        run_command_in_docker(command, s3_client, bucket_name, s3_key, image_name, extra_docker_args=extra_docker_args)

    logging.info("\n[+] Bulut Ortamı (AWS) Zafiyet Analizi modülü tamamlandı.")