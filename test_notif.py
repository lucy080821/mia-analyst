import os, django, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.test.client import Client
from django.contrib.auth.models import User

user = User.objects.first()
if user:
    c = Client()
    c.force_login(user)
    response = c.post('/auth/api/notifications/read-all/')
    print(response.status_code)
    print(response.content)
else:
    print("No user")
