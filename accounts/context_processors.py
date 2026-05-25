from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        # Fetch up to 10 unread notifications for display
        unread_notifications = request.user.notifications.filter(is_read=False)[:10]
        # Count all unread notifications
        unread_count = request.user.notifications.filter(is_read=False).count()
        return {
            'unread_notifications': unread_notifications,
            'unread_notifications_count': unread_count
        }
    return {}
def admin_permissions(request):
    if request.user.is_authenticated and request.user.is_staff:
        try:
            from management.models import AdminPermission
            perms, created = AdminPermission.objects.get_or_create(user=request.user)
            return {'admin_perms': perms}
        except:
            return {}
    return {}
