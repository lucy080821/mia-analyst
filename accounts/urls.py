from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('notifications/', views.notifications_list, name='all_notifications'),
    path('login/', views.MiaLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('upgrade/', views.upgrade, name='upgrade_service'),
    path('payment/<str:reference_code>/', views.process_payment, name='process_payment'),
    path('payment-status/<str:reference_code>/', views.payment_status, name='payment_status'),
    path('payment-webhook/', views.payment_webhook, name='payment_webhook'), # For Casso
    path('payos-webhook/', views.payos_webhook, name='payos_webhook'), # For PayOS
    path('lemon-squeezy-webhook/', views.lemon_squeezy_webhook, name='lemon_squeezy_webhook'), # For Lemon Squeezy
    path('api/update-profile/', views.update_profile_api, name='update_profile_api'),
    path('api/apply-voucher/', views.apply_voucher, name='apply_voucher'),
    path('api/notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # Password Reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]
