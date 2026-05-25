from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('super-admin/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('api/super-ai-chat/', views.super_ai_chat_api, name='super_ai_chat_api'),
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/toggle-staff/', views.toggle_staff_status, name='toggle_staff_status'),
    path('users/<int:user_id>/update-tier/', views.update_user_tier, name='update_user_tier'),
    path('ai-logs/', views.ai_usage_stats, name='ai_usage_stats'),
    path('vouchers/', views.voucher_management, name='voucher_management'),
    path('vouchers/create/', views.create_voucher, name='create_voucher'),
    path('notifications/', views.notification_management, name='notification_management'),
    # Finance
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/add-expense/', views.add_expense, name='add_expense'),
    path('finance/delete-expense/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('permissions/', views.permissions_management, name='permissions_management'),
    path('super-chat/', views.super_ai_chat, name='super_ai_chat'),
    path('system/', views.system_management, name='system_management'),
    
    # Mia Control (Super Admin versions)
    path('super/users/', views.super_user_management, name='super_user_management'),
    path('super/ai-logs/', views.super_ai_usage_stats, name='super_ai_usage_stats'),
    path('super/vouchers/', views.super_voucher_management, name='super_voucher_management'),
    path('super/notifications/', views.super_notification_management, name='super_notification_management'),
    path('super/finance/', views.super_finance_dashboard, name='super_finance_dashboard'),
    path('api/workflow-intelligence/<int:workflow_id>/', views.analyze_workflow_intelligence, name='workflow_intelligence_api'),
]
