from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Transaction, VoucherUsage, Notification

@receiver(post_save, sender=UserProfile)
def welcome_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.user,
            title="Chào mừng bạn đến với Mia Assistant! 🚀",
            message="Chúc mừng bạn đã gia nhập cộng đồng phân tích dữ liệu thông minh. Hãy bắt đầu bằng việc tải lên file Excel hoặc CSV đầu tiên của bạn nhé!",
            link="/analytics/"
        )

@receiver(post_save, sender=Transaction)
def payment_success_notification(sender, instance, created, **kwargs):
    # We trigger notification when status changes to SUCCESS
    if instance.status == 'SUCCESS':
        # Check if a notification for this specific transaction already exists to avoid duplicates
        # (Though status update might happen multiple times if not careful)
        tier_names = {
            'BASIC': 'Cơ bản',
            'ADVANCED': 'Nâng cao',
            'ENTERPRISE': 'Doanh nghiệp'
        }
        tier_name = tier_names.get(instance.tier_requested, instance.tier_requested)
        title = f"Thanh toán thành công gói {tier_name}! ✨"
        message = f"Giao dịch {instance.reference_code} đã được xác nhận. Tài khoản của bạn đã được nâng cấp. Chúc bạn có những trải nghiệm tuyệt vời!"
        
        # Simple check to avoid spamming the same success notification
        if not Notification.objects.filter(user=instance.user, title=title).exists():
            Notification.objects.create(
                user=instance.user,
                title=title,
                message=message,
                link="/auth/profile/"
            )

@receiver(post_save, sender=VoucherUsage)
def voucher_applied_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            user=instance.user,
            title="Áp dụng Voucher thành công! 🎟️",
            message=f"Mã {instance.voucher.code} đã được áp dụng cho tài khoản của bạn. Hãy tận hưởng ưu đãi ngay nhé!",
            link="/auth/upgrade/"
        )
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
