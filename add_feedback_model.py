from django.db import models
from django.contrib.auth.models import User

# This will just append to management/models.py
model_code = '''

class UserFeedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người dùng (nếu có)")
    customer_name = models.CharField(max_length=255, verbose_name="Tên Khách Hàng (Tự nhập)")
    service_package = models.CharField(max_length=100, verbose_name="Gói dịch vụ")
    content = models.TextField(verbose_name="Nội dung Feedback")
    status = models.CharField(max_length=50, default="Chưa đọc", verbose_name="Trạng thái")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày gửi")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Feedback'
        verbose_name_plural = 'User Feedbacks'

    def __str__(self):
        return f"{self.customer_name} - {self.service_package} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
'''

with open(r'C:\Leo Harrison\Mia Analyst\management\models.py', 'a', encoding='utf-8') as f:
    f.write(model_code)
