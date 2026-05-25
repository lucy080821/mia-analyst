
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from analytics.models import UserDataset
datasets = UserDataset.objects.all()
for ds in datasets:
    print(ds.name, ds.table_name)

