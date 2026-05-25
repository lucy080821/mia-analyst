from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Kiểm tra và hạ cấp các tài khoản hết hạn gói dịch vụ'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_profiles = UserProfile.objects.filter(
            subscription_end_date__lt=now,
            tier__in=['PLUS', 'PREMIUM']
        )
        
        count = expired_profiles.count()
        for profile in expired_profiles:
            old_tier = profile.tier
            profile.tier = 'FREE'
            profile.subscription_end_date = None
            profile.save()
            self.stdout.write(self.style.SUCCESS(f'Đã hạ cấp {profile.user.username} từ {old_tier} xuống FREE'))
            
        self.stdout.write(self.style.SUCCESS(f'Hoàn tất kiểm tra. Đã xử lý {count} tài khoản.'))
