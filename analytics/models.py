from django.db import models
from django.contrib.auth.models import User
import uuid

class ReportExportLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    format = models.CharField(max_length=10) # 'word' or 'pdf'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} exported {self.format} at {self.timestamp}"

class CustomDashboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    layout_json = models.JSONField(null=True, blank=True) # Stores Gridstack widget positions/sizes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class DashboardWidget(models.Model):
    dashboard = models.ForeignKey(CustomDashboard, related_name='widgets', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    
    # AI Mode
    query = models.TextField(null=True, blank=True) # Saved AI question/query
    
    # Manual Mode
    data_source = models.ForeignKey('UserDataset', on_delete=models.SET_NULL, null=True, blank=True)
    label_col = models.CharField(max_length=255, null=True, blank=True)
    value_col = models.CharField(max_length=255, null=True, blank=True)
    agg_func = models.CharField(max_length=20, default='SUM') # SUM, AVG, COUNT, MIN, MAX
    
    chart_type = models.CharField(max_length=50, default='bar') # bar, line, pie, doughnut, metric
    style_config = models.JSONField(null=True, blank=True) # stores colors, fonts, etc.
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} in {self.dashboard.name}"

class TelegramSettings(models.Model):
    bot_token = models.CharField(max_length=255)
    chat_id = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Telegram Bot: {self.bot_token[:10]}..."

class AutomationTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default="Default Task")
    dataset = models.ForeignKey('UserDataset', on_delete=models.SET_NULL, null=True, blank=True)
    gsheet_url = models.URLField(max_length=500, null=True, blank=True)
    analysis_prompt = models.TextField()
    schedule_time = models.TimeField()
    schedule_type = models.CharField(max_length=20, default='daily') # daily, weekly, monthly
    schedule_days = models.CharField(max_length=100, null=True, blank=True) # "1,2,3" or "first,last"
    timezone = models.CharField(max_length=50, default='UTC')
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username} ({self.schedule_time})"

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    response_text = models.TextField()
    response_data = models.JSONField(null=True, blank=True) # Để lưu bảng dữ liệu hoặc config biểu đồ
    response_type = models.CharField(max_length=20, default='text') # text, table, chart, dashboard
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.question[:30]}..."

class FileUploadLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    file_size_kb = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} uploaded {self.filename}"

class UserActionLog(models.Model):
    ACTION_CHOICES = [
        ('SAVE_REPORT', 'Lưu báo cáo'),
        ('DOWNLOAD_CHART', 'Tải biểu đồ'),
        ('SHARE_LINK', 'Chia sẻ liên kết'),
        ('COPY_SQL', 'Sao chép SQL'),
        ('JOIN_TABLES', 'Join bảng'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_action_type_display()}"

class ShopeeCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shopee_creds')
    shop_id = models.BigIntegerField()
    access_token_enc = models.TextField()
    refresh_token_enc = models.TextField()
    expire_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Shopee Shop {self.shop_id} ({self.user.username})"

class ShopeeOrder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop_id = models.BigIntegerField()
    order_sn = models.CharField(max_length=50, unique=True)
    order_status = models.CharField(max_length=50)
    create_time = models.DateTimeField()
    pay_time = models.DateTimeField(null=True, blank=True)
    
    # Financial fields (Flat for EDA)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    actual_shipping_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    estimated_shipping_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Escrow Fields
    escrow_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    seller_transaction_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    commission_fee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Rebates & Vouchers
    seller_rebate = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    shopee_rebate = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    voucher_seller = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    voucher_shopee = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    buyer_username = models.CharField(max_length=255, null=True, blank=True)
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'shop_id']),
            models.Index(fields=['create_time']),
        ]

    def __str__(self):
        return f"Order {self.order_sn} - {self.user.username}"

class VisitorSession(models.Model):
    session_key = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Session {self.session_key[:8]} - {self.duration_seconds}s"

class UserDataset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    table_name = models.CharField(max_length=255, unique=True) # SQLite internal table name
    original_filename = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, default='upload') # upload, gsheet, api, shopee, PIPELINE
    source_url = models.URLField(max_length=500, null=True, blank=True)
    connector = models.ForeignKey('DatabaseCredential', on_delete=models.SET_NULL, null=True, blank=True)
    source_sql = models.TextField(null=True, blank=True) # Stores the JOIN SQL for PIPELINE datasets
    row_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(null=True, blank=True)

    # Auto-refresh settings (for source_type='gsheet')
    is_auto_refresh = models.BooleanField(default=False)
    refresh_interval = models.CharField(max_length=20, choices=[
        ('hourly', 'Hàng giờ'),
        ('daily', 'Hàng ngày'),
        ('weekly', 'Hàng tuần')
    ], default='daily')

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class DatasetRelationship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_dataset = models.ForeignKey(UserDataset, on_delete=models.CASCADE, related_name='source_links')
    source_column = models.CharField(max_length=255)
    target_dataset = models.ForeignKey(UserDataset, on_delete=models.CASCADE, related_name='target_links')
    target_column = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source_dataset.name}.{self.source_column} -> {self.target_dataset.name}.{self.target_column}"

class CalculatedField(models.Model):
    dataset = models.ForeignKey(UserDataset, on_delete=models.CASCADE, related_name='calculations')
    name = models.CharField(max_length=255)
    formula = models.TextField()
    type = models.CharField(max_length=20, choices=[('MEASURE', 'Measure'), ('COLUMN', 'Column')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.type}) on {self.dataset.name}"

class DatabaseCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='db_creds')
    name = models.CharField(max_length=255) # e.g., "My MySQL ERP"
    db_type = models.CharField(max_length=50, choices=[('mysql', 'MySQL'), ('postgres', 'PostgreSQL'), ('sqlserver', 'SQL Server')])
    host = models.CharField(max_length=255)
    port = models.IntegerField()
    database_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password_enc = models.TextField() # Encrypted using Fernet
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.db_type}) - {self.user.username}"

class ApiCredential(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_creds')
    platform = models.CharField(max_length=50, choices=[('kiotviet', 'KiotViet'), ('facebook_ads', 'Facebook Ads'), ('google_ads', 'Google Ads/AdSense')])
    name = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255, null=True, blank=True)
    api_key_enc = models.TextField() # Encrypted using Fernet
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform} - {self.name} ({self.user.username})"

class ELTWorkflow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elt_workflows')
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    user_intent = models.TextField(help_text="Yêu cầu bằng tiếng Việt để AI sinh SQL phân tích")
    schedule_interval = models.CharField(max_length=50, default='daily') # hourly, daily, weekly
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workflow: {self.name} ({self.user.username})"

class ELTPipelineLog(models.Model):
    workflow = models.ForeignKey(ELTWorkflow, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20, choices=[('RUNNING', 'Đang chạy'), ('SUCCESS', 'Thành công'), ('FAILED', 'Thất bại')])
    error_message = models.TextField(null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Log {self.id} for {self.workflow.name} - {self.status}"

class AnomalyAlertConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    dataset = models.ForeignKey(UserDataset, on_delete=models.CASCADE)
    metric_col = models.CharField(max_length=255)
    threshold_pct = models.IntegerField(default=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_checked = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Alert: {self.dataset.name} ({self.metric_col} > {self.threshold_pct}%) - {self.user.username}"

class SharedReport(models.Model):
    uuid_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Báo cáo phân tích")
    config_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Report: {self.title} by {self.user.username}"

class AutomationLog(models.Model):
    task = models.ForeignKey(AutomationTask, on_delete=models.CASCADE, related_name='logs')
    status = models.CharField(max_length=20) # SUCCESS, FAILED
    message = models.TextField(null=True, blank=True) # Short summary or error
    run_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.id} for {self.task.name} - {self.status}"
