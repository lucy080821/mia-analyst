from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import UserProfile
from analytics.models import ReportExportLog, CustomDashboard, DashboardWidget
from django.urls import reverse
import json
from django.utils import timezone
from datetime import timedelta

class AnalyticsExportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.free_user = User.objects.create_user(username='free_user', password='password')
        self.plus_user = User.objects.create_user(username='plus_user', password='password')
        self.premium_user = User.objects.create_user(username='premium_user', password='password')
        
        UserProfile.objects.create(user=self.free_user, tier='FREE')
        UserProfile.objects.create(user=self.plus_user, tier='PLUS')
        UserProfile.objects.create(user=self.premium_user, tier='PREMIUM')

    def test_free_user_export_denied(self):
        self.client.login(username='free_user', password='password')
        response = self.client.post(reverse('export_report'), 
                                    data=json.dumps({'content': 'Test', 'format': 'word'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('Vui lòng nâng cấp', response.json()['error'])

    def test_plus_user_export_limit(self):
        self.client.login(username='plus_user', password='password')
        url = reverse('export_report')
        
        # 5 successful exports
        for _ in range(5):
            response = self.client.post(url, 
                                        data=json.dumps({'content': 'Test', 'format': 'word'}),
                                        content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        
        # 6th export should be denied
        response = self.client.post(url, 
                                    data=json.dumps({'content': 'Test', 'format': 'word'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('giới hạn', response.json()['error'])

    def test_premium_user_unlimited_export(self):
        self.client.login(username='premium_user', password='password')
        url = reverse('export_report')
        
        # More than 5 exports
        for _ in range(7):
            response = self.client.post(url, 
                                        data=json.dumps({'content': 'Test', 'format': 'word'}),
                                        content_type='application/json')
            self.assertEqual(response.status_code, 200)

    def test_dashboard_manager_premium_only(self):
        url = reverse('dashboard_manager')
        
        # PLUS user denied
        self.client.login(username='plus_user', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
        # PREMIUM user allowed
        self.client.login(username='premium_user', password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('dashboards', response.json())

    def test_create_dashboard_and_add_widget(self):
        self.client.login(username='premium_user', password='password')
        url = reverse('dashboard_manager')
        
        # Create dashboard
        response = self.client.post(url, 
                                    data=json.dumps({'action': 'create', 'name': 'Test DB'}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        db_id = response.json()['id']
        
        # Add widget
        response = self.client.post(url, 
                                    data=json.dumps({
                                        'action': 'add_widget', 
                                        'dashboard_id': db_id,
                                        'title': 'Test Widget',
                                        'query': 'SELECT * FROM temp'
                                    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        # Verify
        db = CustomDashboard.objects.get(id=db_id)
        self.assertEqual(db.widgets.count(), 1)
        self.assertEqual(db.widgets.first().title, 'Test Widget')
