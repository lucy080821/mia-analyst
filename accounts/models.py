from django.db import models
from django.contrib.auth.models import User

TIER_CHOICES = [
    ('BASIC', 'Cơ bản'),
    ('FREE', 'Cơ bản'),
    ('ADVANCED', 'Nâng cao'),
    ('PLUS', 'Nâng cao'),
    ('ENTERPRISE', 'Doanh nghiệp'),
    ('PREMIUM', 'Doanh nghiệp'),
]

GENDER_CHOICES = [
    ('M', 'Nam'),
    ('F', 'Nữ'),
    ('O', 'Khác'),
]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='BASIC')
    subscription_start_date = models.DateTimeField(null=True, blank=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    is_first_login = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.tier}"

    @property
    def customer_code(self):
        """
        Mã KH: yymmdd + ID
        Example: 240515123 (Joined May 15, 2024, ID 123)
        """
        date_part = self.user.date_joined.strftime('%y%m%d')
        return f"{date_part}{self.user.id}"

class Transaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ'),
        ('SUCCESS', 'Thành công'),
        ('FAILED', 'Thất bại'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    tier_requested = models.CharField(max_length=10)
    reference_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.reference_code} - {self.status}"

class Voucher(models.Model):
    VOUCHER_TYPES = [
        ('FREE_ADVANCED_7_DAYS', 'Miễn phí Nâng cao 7 ngày'),
        ('DISCOUNT_PERCENT', 'Giảm % cho tất cả gói'),
        ('FIXED_DISCOUNT', 'Giảm số tiền cố định'),
    ]
    code = models.CharField(max_length=50, unique=True)
    voucher_type = models.CharField(max_length=50, choices=VOUCHER_TYPES)
    discount_val = models.IntegerField(null=True, blank=True, help_text="Tỷ lệ % hoặc số tiền cố định")
    max_uses = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def current_uses(self):
        return self.voucherusage_set.count()

    def __str__(self):
        return f"{self.code} - {self.get_voucher_type_display()}"

class VoucherUsage(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('voucher', 'user')

    def __str__(self):
        return f"{self.user.username} used {self.voucher.code}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{'Read' if self.is_read else 'Unread'}] {self.user.username}: {self.title}"

