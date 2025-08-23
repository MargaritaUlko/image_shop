import os
from celery import Celery

# Устанавливаем переменную окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')

app = Celery('your_project_name')

# Используем настройки Django с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим tasks.py в Django приложениях
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')