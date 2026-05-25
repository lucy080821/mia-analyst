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

def user_profile(request):
    """Inject user profile (avatar, display_name) into every template context."""
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            full_name = f"{profile.first_name} {profile.last_name}".strip()
            if not full_name:
                full_name = request.user.get_full_name() or request.user.username
            # Lấy 2 từ cuối của fullname để chào
            name_parts = full_name.split()
            display_name = " ".join(name_parts[-2:]) if len(name_parts) >= 2 else full_name
            return {
                'user_profile': profile,
                'global_display_name': display_name,
                'global_avatar_url': profile.avatar.url if profile.avatar else None,
            }
        except Exception:
            pass
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

