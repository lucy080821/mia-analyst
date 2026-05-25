from django.utils import timezone
from datetime import timedelta
from .models import Notification

class NotificationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self.check_subscription_expiry(request.user)
        
        response = self.get_response(request)
        return response

    def check_subscription_expiry(self, user):
        try:
            profile = user.userprofile
            if profile.subscription_end_date:
                now = timezone.now()
                # Check if it expires in the next 7 days
                if now <= profile.subscription_end_date <= (now + timedelta(days=7)):
                    title = "Nhắc nhở gia hạn! ⏳"
                    # Check if we already sent a reminder in the last 7 days to avoid spam
                    recent_notif = Notification.objects.filter(
                        user=user, 
                        title=title, 
                        created_at__gte=now - timedelta(days=7)
                    ).exists()
                    
                    if not recent_notif:
                        Notification.objects.create(
                            user=user,
                            title=title,
                            message=f"Gói {profile.get_tier_display()} của bạn sẽ hết hạn trong vòng 1 tuần tới ({profile.subscription_end_date.strftime('%d/%m/%Y')}). Hãy gia hạn sớm để không gián đoạn công việc nhé!",
                            link="/auth/upgrade/"
                        )
        except Exception:
            pass
