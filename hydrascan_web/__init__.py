# Bu dosya (hydrascan_web/__init__.py)

# Django başladığında bu uygulamanın yüklenmesini garanti eder,
# böylece @shared_task dekoratörleri bu uygulamayı kullanır.
from .celery import app as celery_app

__all__ = ('celery_app',)