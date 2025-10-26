# core/cloud_module.py (YENİ - YEREL HALİ)

import os
import logging
# Importu düzeltelim
from core.docker_helper import run_command_in_docker

# DEĞİŞİKLİK: 's3_client', 'bucket_name', 's3_prefix' parametreleri
# 'output_dir' ile değişti.
# Ayrıca AWS anahtarları artık scan_data'dan gelecek.
def run_cloud_tests(access_key, secret_key, region, image_name, output_dir):
    """
    Bulut (AWS) ortamı test araçlarını çalıştırır ve çıktıları yerel output_dir içine kaydeder.
    """
    logging.info("\n[+] 6. Bulut Ortamı (AWS) Zafiyet Analizi modülü başlatılıyor...")

    # Docker konteynerine AWS anahtarlarını environment variable olarak geçir
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
        # DEĞİŞİKLİK: Tam dosya yolu oluşturuyoruz
        output_file_path = os.path.join(output_dir, output_filename)
        
        # docker_helper'a yerel dosya yolunu VE extra_docker_args'ı iletiyoruz
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=extra_docker_args)

    logging.info("\n[+] Bulut Ortamı (AWS) Zafiyet Analizi modülü tamamlandı.")