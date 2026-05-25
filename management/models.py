from django.db import models
from django.contrib.auth.models import User


class PlatformExpense(models.Model):
    CATEGORY_CHOICES = [
        ('SERVER', 'Chi phí Server / Hosting'),
        ('AI_API', 'Chi phí AI API (Gemini, OpenAI...)'),
        ('DOMAIN', 'Tên miền / SSL'),
        ('MARKETING', 'Marketing / Quảng cáo'),
        ('TOOLS', 'Công cụ / Phần mềm'),
        ('SALARY', 'Lương / Nhân sự'),
        ('TAX', 'Thuế / Phí pháp lý'),
        ('OTHER', 'Chi phí khác'),
    ]
    title = models.CharField(max_length=255, verbose_name='Tên khoản chi')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER', verbose_name='Danh mục')
    amount = models.DecimalField(max_digits=14, decimal_places=0, verbose_name='Số tiền (VNĐ)')
    note = models.TextField(blank=True, verbose_name='Ghi chú')
    expense_date = models.DateField(verbose_name='Ngày chi')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount:,}đ ({self.expense_date})"

    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name = 'Khoản chi'
        verbose_name_plural = 'Các khoản chi'


class AIUsageLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    model_name = models.CharField(max_length=50)
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='SUCCESS')
    timestamp = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)
    
    # New Actionable Metrics Fields
    processing_time = models.FloatField(default=0) # TTV (seconds)
    is_correction = models.BooleanField(default=False)
    file_size_kb = models.IntegerField(default=0)
    feedback_stars = models.IntegerField(null=True, blank=True) # 1-5
    is_regenerated = models.BooleanField(default=False)
    error_type = models.CharField(max_length=50, blank=True, null=True) # Token, Timeout, etc.

    def __str__(self):
        return f"{self.user} - {self.model_name} - {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
class AdminPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_permission')
    can_view_finance = models.BooleanField(default=False, verbose_name='Xem tài chính')
    can_view_users = models.BooleanField(default=False, verbose_name='Quản lý người dùng')
    can_view_ai_logs = models.BooleanField(default=False, verbose_name='Xem AI Logs')
    can_view_vouchers = models.BooleanField(default=False, verbose_name='Quản lý Voucher')
    can_view_notifications = models.BooleanField(default=False, verbose_name='Quản lý Thông báo')
    can_view_system = models.BooleanField(default=False, verbose_name='Quản lý Hệ thống')
    can_view_blog = models.BooleanField(default=True, verbose_name='Quản lý Blog')
    role_title = models.CharField(max_length=50, blank=True, null=True, verbose_name='Vị trí/Chức vụ')

    def __str__(self):
        return f"Permissions for {self.user.username}"

    class Meta:
        verbose_name = 'Phân quyền Admin'
        verbose_name_plural = 'Phân quyền Admin'


class SecurityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.TextField(verbose_name="Nội dung câu hỏi")
    is_malicious = models.BooleanField(default=False, verbose_name="Phát hiện độc hại")
    analysis_reason = models.TextField(blank=True, null=True, verbose_name="Lý do (AI phân tích)")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Nhật ký Bảo mật AI'
        verbose_name_plural = 'Nhật ký Bảo mật AI'

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        status = "MALICIOUS" if self.is_malicious else "SAFE"
        return f"[{status}] {username} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class SalesLead(models.Model):
    session_id = models.CharField(max_length=255, unique=True, verbose_name="Phiên Chat")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người dùng")
    collected_info = models.JSONField(default=dict, blank=True, verbose_name="Thông tin thu thập")
    chat_history = models.JSONField(default=list, blank=True, verbose_name="Lịch sử Chat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Khách hàng tiềm năng'
        verbose_name_plural = 'Khách hàng tiềm năng'

    def __str__(self):
        return f"Lead: {self.session_id} - {self.updated_at.strftime('%Y-%m-%d %H:%M')}"


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
