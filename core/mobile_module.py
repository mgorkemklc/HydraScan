import os
from docker_helper import run_command_in_docker

def run_mobile_tests(apk_path, output_dir, image_name):
    """
    Belirtilen .apk dosyası üzerinde statik analiz testleri gerçekleştirir.

    Args:
        apk_path (str): Analiz edilecek .apk dosyasının tam yolu.
        output_dir (str): Çıktıların kaydedileceği dizin.
        image_name (str): Kullanılacak Docker imajı.
    """
    print("\n[+] Mobil Uygulama (Statik Analiz) Testleri modülü başlatılıyor...")

    if not os.path.exists(apk_path):
        print(f"[-] Hata: Belirtilen .apk dosyası bulunamadı: {apk_path}")
        return

    # APK dosyasının bulunduğu dizini ve dosya adını al
    apk_dir = os.path.dirname(apk_path)
    apk_filename = os.path.basename(apk_path)

    # APK dosyasının bulunduğu dizini container içinde /app olarak bağla
    # Bu sayede container içindeki araçlar dosyaya erişebilir.
    docker_mount_args = ['-v', f'{os.path.abspath(apk_dir)}:/app']

    # Container içinde çalıştırılacak komutlar
    commands = {
        # 1. Adım: apkleaks ile APK içinde hardcoded sırlar, URL'ler ve hassas bilgiler ara
        "apkleaks_ciktisi.txt": f"apkleaks -f /app/{apk_filename}",

        # 2. Adım: apktool ile APK dosyasını kaynaklarına ayır.
        # Bu komutun çıktısı bir metin değil, bir klasör dolusu dosyadır.
        # Bu nedenle çıktısı Gemini'ye gönderilmez, manuel analiz için saklanır.
        "apktool_decompile_ciktisi.txt": f"apktool d /app/{apk_filename} -o /output/apktool_decompiled -f"
    }

    for output_filename, command in commands.items():
        output_file_path = os.path.join(output_dir, output_filename)
        # Komutları, APK'nın bulunduğu dizini mount ederek çalıştır
        run_command_in_docker(command, output_file_path, image_name, extra_docker_args=docker_mount_args)

    print("\n[+] Mobil Uygulama Testleri modülü tamamlandı.")
    print(f"[i] apktool çıktıları manuel analiz için '{os.path.join(output_dir, 'apktool_decompiled')}' dizinine kaydedildi.")