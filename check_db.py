
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.conf import settings
print('DATABASE ENGINE:', settings.DATABASES['default']['ENGINE'])
print('DATABASE NAME:', settings.DATABASES['default']['NAME'])

