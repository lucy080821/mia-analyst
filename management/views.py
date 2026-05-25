from datetime import datetime, timedelta
from functools import wraps
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, Avg, Max
from django.db.models.functions import TruncDate
from django.contrib import messages
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt    
from django.conf import settings
from django.core.exceptions import PermissionDenied

from core.views import get_template_name
from accounts.models import UserProfile, Transaction, Voucher, VoucherUsage, Notification
from analytics.models import FileUploadLog, UserActionLog, VisitorSession, UserDataset, DatabaseCredential, ApiCredential, ELTWorkflow, ELTPipelineLog
from blog.models import Post, ReadingSession
from management.models import AIUsageLog, PlatformExpense, AdminPermission
from management.utils import export_to_excel

def super_admin_only(user):
    # Admin tối cao: leo12121993
    return user.is_authenticated and (user.username == 'leo12121993' or user.is_superuser)

def _parse_date_range(request):
    """Helper to parse start_date and end_date from request GET parameters."""
    today = datetime.now().date()
    end_date_str = request.GET.get('end_date')
    start_date_str = request.GET.get('start_date')
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
        
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = end_date - timedelta(days=6)
    else:
        start_date = end_date - timedelta(days=6)
        
    return start_date, end_date


def admin_permission_required(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if super_admin_only(request.user):
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_staff:
                raise PermissionDenied
            
            perms, _ = AdminPermission.objects.get_or_create(user=request.user)
            if getattr(perms, permission_name, False):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"Bạn không có quyền truy cập vào mục này.")
            return redirect('admin_dashboard')
        return _wrapped_view
    return decorator

@user_passes_test(super_admin_only)
def super_admin_dashboard(request):
    # --- 1. Basic Setup & Filtering ---
    start_date, end_date = _parse_date_range(request)
    today = datetime.now().date()

    # --- 2. System-wide Stats (All Time Totals) ---
    total_users = User.objects.count()
    plus_users = UserProfile.objects.filter(tier__in=['PLUS', 'ADVANCED']).count()
    premium_users = UserProfile.objects.filter(tier__in=['PREMIUM', 'ENTERPRISE']).count()
    free_users = total_users - (plus_users + premium_users)
    new_users_today = User.objects.filter(date_joined__date=today).count()
    
    total_revenue = Transaction.objects.filter(status='SUCCESS').aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = PlatformExpense.objects.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = total_revenue - total_expenses

    # --- 3. AI & Data Pipeline Stats ---
    total_ai_calls = AIUsageLog.objects.count()
    ai_success_rate = (AIUsageLog.objects.filter(status='SUCCESS').count() / total_ai_calls * 100) if total_ai_calls > 0 else 0
    total_connectors = DatabaseCredential.objects.count() + ApiCredential.objects.count()
    total_workflows = ELTWorkflow.objects.count()
    active_workflows = ELTWorkflow.objects.filter(is_active=True).count()
    
    latest_log_ids = ELTPipelineLog.objects.values('workflow').annotate(max_id=Max('id')).values_list('max_id', flat=True)
    recent_logs = ELTPipelineLog.objects.filter(id__in=latest_log_ids).order_by('-start_time')[:10]
    total_pipeline_runs = ELTPipelineLog.objects.count()
    pipeline_success_rate = (ELTPipelineLog.objects.filter(status='SUCCESS').count() / total_pipeline_runs * 100) if total_pipeline_runs > 0 else 0
    # --- 4. Content & Marketing Stats ---
    total_posts = Post.objects.count()
    total_blog_views = Post.objects.aggregate(total=Sum('total_views'))['total'] or 0
    total_reading_sessions = ReadingSession.objects.count()
    avg_scroll_depth = ReadingSession.objects.aggregate(avg=Avg('scroll_depth'))['avg'] or 0

    total_vouchers = Voucher.objects.count()
    active_vouchers = Voucher.objects.filter(is_active=True).count()
    total_voucher_uses = VoucherUsage.objects.count()
    
    # Global Notifications for System Monitor
    total_notifications_global = Notification.objects.count()
    unread_notifications_global = Notification.objects.filter(is_read=False).count()
    # --- 5. Data Warehouse Stats ---
    total_datasets = UserDataset.objects.count()
    total_rows = UserDataset.objects.aggregate(total=Sum('row_count'))['total'] or 0

    # --- 6. Actionable Metrics (Filtered by Range) ---
    usage_filtered = AIUsageLog.objects.filter(timestamp__date__range=[start_date, end_date])
    tx_filtered = Transaction.objects.filter(status='SUCCESS', created_at__date__range=[start_date, end_date])
    
    # Engagement
    total_uploads = FileUploadLog.objects.filter(timestamp__date__range=[start_date, end_date]).count()
    user_days = usage_filtered.values('user', 'timestamp__date').distinct().count()
    engagement = {
        'avg_uploads': (total_uploads / total_users) if total_users > 0 else 0,
        'session_depth': (usage_filtered.count() / user_days) if user_days > 0 else 0,
        'avg_ttv': usage_filtered.aggregate(Avg('processing_time'))['processing_time__avg'] or 0,
    }

    # Quality
    usage_count = usage_filtered.count()
    saves_count = UserActionLog.objects.filter(action_type__in=['SAVE_REPORT', 'DOWNLOAD_CHART'], timestamp__date__range=[start_date, end_date]).count()
    corrections_count = usage_filtered.filter(is_correction=True).count()
    negative_feedback_count = usage_filtered.filter(Q(feedback_stars__lte=2) | Q(is_regenerated=True)).count()
    quality = {
        'acceptance_rate': (saves_count / usage_count * 100) if usage_count > 0 else 0,
        'correction_rate': (corrections_count / usage_count * 100) if usage_count > 0 else 0,
        'negative_loop': (negative_feedback_count / usage_count * 100) if usage_count > 0 else 0,
    }

    # Growth
    exports_shares = UserActionLog.objects.filter(action_type__in=['SHARE_LINK', 'DOWNLOAD_CHART'], timestamp__date__range=[start_date, end_date]).count()
    active_old_users = usage_filtered.filter(user__date_joined__date__lt=start_date).values('user').distinct().count()
    total_old_users = User.objects.filter(date_joined__date__lt=start_date).count()
    growth = {
        'share_rate': (exports_shares / usage_filtered.count() * 100) if usage_filtered.count() > 0 else 0,
        'retention_30d': (active_old_users / total_old_users * 100) if total_old_users > 0 else 0,
    }

    # Technical
    technical = {
        'success_rate': (usage_filtered.filter(status='SUCCESS').count() / usage_filtered.count() * 100) if usage_filtered.count() > 0 else 0,
        'data_token_ratio': usage_filtered.aggregate(Avg('file_size_kb'))['file_size_kb__avg'] or 0,
    }

    # --- 7. Trend Data for Charts ---
    usage_labels, usage_counts = [], []
    revenue_labels, revenue_amounts = [], []
    delta = (end_date - start_date).days
    
    usage_trend = usage_filtered.annotate(day=TruncDate('timestamp')).values('day').annotate(count=Count('id')).order_by('day')
    usage_dict = {item['day']: item['count'] for item in usage_trend}
    
    revenue_trend = tx_filtered.annotate(day=TruncDate('created_at')).values('day').annotate(total=Sum('amount')).order_by('day')
    revenue_dict = {item['day']: float(item['total']) for item in revenue_trend}

    for i in range(delta + 1):
        d = start_date + timedelta(days=i)
        usage_labels.append(d.strftime('%d/%m'))
        usage_counts.append(usage_dict.get(d, 0))
        revenue_labels.append(d.strftime('%d/%m'))
        revenue_amounts.append(revenue_dict.get(d, 0))

    context = {
        # Basics
        'is_super': True,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        
        # Totals
        'total_users': total_users,
        'free_users': free_users,
        'plus_users': plus_users,
        'premium_users': premium_users,
        'new_users_today': new_users_today,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        
        # AI & Pipeline
        'total_ai_calls': total_ai_calls,
        'ai_success_rate': round(ai_success_rate, 1),
        'total_connectors': total_connectors,
        'total_workflows': total_workflows,
        'active_workflows': active_workflows,
        'recent_pipeline_logs': recent_logs,
        'pipeline_success_rate': round(pipeline_success_rate, 1),
        
        # Content & Marketing
        'total_posts': total_posts,
        'total_blog_views': total_blog_views,
        'total_reading_sessions': total_reading_sessions,
        'avg_scroll_depth': round(avg_scroll_depth * 100, 1),
        'total_vouchers': total_vouchers,
        'active_vouchers': active_vouchers,
        'total_voucher_uses': total_voucher_uses,
        'total_notifications_global': total_notifications_global,
        'unread_notifications_global': unread_notifications_global,
        
        # Warehouse
        'total_datasets': total_datasets,
        'total_rows': total_rows,
        
        # Actionable Metrics
        'engagement': engagement,
        'quality': quality,
        'growth': growth,
        'technical': technical,
        
        # Chart Data
        'usage_labels': json.dumps(usage_labels),
        'usage_counts': json.dumps(usage_counts),
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_amounts': json.dumps(revenue_amounts),
    }
    return render(request, get_template_name(request, 'management/super_admin.html'), context)

@csrf_exempt
@user_passes_test(super_admin_only)
def super_ai_chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        question = body.get("message", "")
        
        # 1. Thu thập dữ liệu vận hành (Context TOÀN DIỆN)

        # --- USERS & FINANCE ---
        total_users = User.objects.count()
        plus_users = UserProfile.objects.filter(tier='PLUS').count()
        premium_users = UserProfile.objects.filter(tier='PREMIUM').count()
        free_users = total_users - (plus_users + premium_users)
        new_users_today = User.objects.filter(date_joined__date=datetime.now().date()).count()
        
        total_revenue = Transaction.objects.filter(status='SUCCESS').aggregate(total=Sum('amount'))['total'] or 0
        total_expenses = PlatformExpense.objects.aggregate(total=Sum('amount'))['total'] or 0
        net_profit = total_revenue - total_expenses

        # --- AI & APIs ---
        ai_calls = AIUsageLog.objects.count()
        ai_success_rate = (AIUsageLog.objects.filter(status='SUCCESS').count() / ai_calls * 100) if ai_calls > 0 else 0
        total_connectors = DatabaseCredential.objects.count() + ApiCredential.objects.count()
        
        # --- BLOG ANALYTICS ---
        total_posts = Post.objects.count()
        total_blog_views = Post.objects.aggregate(total=Sum('total_views'))['total'] or 0
        total_reading_sessions = ReadingSession.objects.count()
        avg_scroll_depth = ReadingSession.objects.aggregate(avg=Avg('scroll_depth'))['avg'] or 0

        # --- VOUCHERS & PROMOTIONS ---
        total_vouchers = Voucher.objects.count()
        active_vouchers = Voucher.objects.filter(is_active=True).count()
        total_voucher_uses = VoucherUsage.objects.count()

        # --- NOTIFICATIONS ---
        total_notifications = Notification.objects.count()
        unread_notifications = Notification.objects.filter(is_read=False).count()

        # --- DATA PIPELINE & WAREHOUSE ---
        total_workflows = ELTWorkflow.objects.count()
        active_workflows = ELTWorkflow.objects.filter(is_active=True).count()
        total_datasets = UserDataset.objects.count()
        total_rows = UserDataset.objects.aggregate(total=Sum('row_count'))['total'] or 0

        # 2. Xây dựng Prompt chiến lược với Chỉ thị "Thông minh chọn lọc"
        lang_target = "English" if any(word in question.lower() for word in ["hi", "hello", "what", "how", "report", "analyze"]) else "Vietnamese"

        system_prompt = f"""You are the CFO & Strategic Growth Advisor for Mia Analyst.
        BACKGROUND KNOWLEDGE (INTERNAL DATA):
        - USERS: Total {total_users} (New today: {new_users_today}). Breakdown: {free_users} Free, {plus_users} Plus, {premium_users} Premium.
        - FINANCE: Revenue {total_revenue} VND, Expenses {total_expenses} VND, Net Profit {net_profit} VND.
        - AI CORE: {ai_calls} total calls, {ai_success_rate:.1f}% success rate.
        - DATA PIPELINE: {total_workflows} workflows ({active_workflows} active), {total_connectors} connectors.
        - WAREHOUSE: {total_datasets} datasets, {total_rows} total rows.
        - BLOG: {total_posts} posts, {total_blog_views} total views, {total_reading_sessions} reading sessions, Avg scroll depth {avg_scroll_depth:.1%}.
        - VOUCHERS: {total_vouchers} vouchers ({active_vouchers} active), Total uses: {total_voucher_uses}.
        - NOTIFICATIONS: {total_notifications} sent, {unread_notifications} unread.
        
        1. Language: {lang_target}.
        2. NO MARKDOWN. Use ONLY the specified HTML structure: <h3>, <p>, <h4>, <div class="metric-grid"><div class="metric-card"><div class="metric-label">...</div><div class="metric-value">...</div></div></div>, <div class="insight-box">.
        3. IMPORTANT: Put ALL related metric-cards inside a SINGLE <div class="metric-grid"> container. This ensures cards are arranged HORIZONTALLY.
        4. NUMBER FORMATTING: Always use thousand separators for large numbers (e.g., 1,234,567 instead of 1234567).
        
        STRICT OUTPUT RULES:
        1. Language: Use Vietnamese for all content.
        2. Content: The 'html' field is for a concise executive summary only.
        3. Dashboard: You MUST provide a structured 'dashboard' object for all platform reports.
        
        RESPONSE FORMAT (JSON):
        {{
          "html": "<h3>Tóm tắt chiến lược</h3><p>...</p>",
          "dashboard": {{
            "title": "Dashboard Title",
            "metrics": [{{ "label": "Metric Name", "value": "Value", "trend": number_or_null }}],
            "charts": [{{ "title": "Chart Title", "type": "bar/line/pie", "columns": ["X", "Y"], "data": [{{ "X": "Label", "Y": 10 }}] }}],
            "insight": "Strategic analysis and actionable advice for the founder..."
          }}
        }}
        
        CRITICAL RULES:
        1. If the user asks for a 'dashboard', 'report', 'summary', or 'sức khỏe', you MUST return a populated 'dashboard' object.
        2. Use professional business language.
        3. The 'html' field should not contain any data cards or grids.
        """

        # 3. Cấu hình & Gọi AI: Sử dụng model resolver an toàn
        from analytics.ai_utils import get_generative_model
        ai_model = get_generative_model()
        response = ai_model.generate_content(
            [system_prompt, f"USER QUESTION: {question}"],
            generation_config={"response_mime_type": "application/json"}
        )
        
        return JsonResponse(json.loads(response.text))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"html": f"<p class='text-rose-500'>Lỗi hệ thống: {str(e)}</p>", "dashboard": None}, status=500)

@staff_member_required
def admin_dashboard(request):

    # Date Filtering Logic
    start_date, end_date = _parse_date_range(request)
    today = datetime.now().date()
    
    # Initialize these so they're available for Excel export even if not is_super
    traffic_filtered = VisitorSession.objects.filter(start_time__date__range=[start_date, end_date])

    # User Stats (Total is still total, but we can also count new users in range)
    total_users = User.objects.count()
    new_users_in_range = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
    
    free_users = UserProfile.objects.filter(tier='FREE').count()
    plus_users = UserProfile.objects.filter(tier='PLUS').count()
    premium_users = UserProfile.objects.filter(tier='PREMIUM').count()
 
    # AI Stats (Filtered)
    usage_filtered = AIUsageLog.objects.filter(timestamp__date__range=[start_date, end_date])
    total_ai_calls = usage_filtered.count()
    success_ai_calls = usage_filtered.filter(status='SUCCESS').count()
    
    ai_success_rate = 0
    if total_ai_calls > 0:
        ai_success_rate = (success_ai_calls / total_ai_calls) * 100
    
    # Financial Stats (Estimated Monthly Revenue - Usually based on CURRENT tiers)
    estimated_revenue = (plus_users * 199000) + (premium_users * 499000)
 
    # Actual Revenue (Filtered)
    tx_filtered = Transaction.objects.filter(status='SUCCESS', created_at__date__range=[start_date, end_date])
    actual_revenue = tx_filtered.aggregate(total=Sum('amount'))['total'] or 0
    
    # 1. AI Usage Trend (For the selected range)
    usage_trend_data = usage_filtered \
        .annotate(day=TruncDate('timestamp')) \
        .values('day') \
        .annotate(count=Count('id')) \
        .order_by('day')
    
    # Fill gaps in the selected range
    usage_labels = []
    usage_counts = []
    trend_dict = {item['day']: item['count'] for item in usage_trend_data}
    
    delta = (end_date - start_date).days
    for i in range(delta + 1):
        d = start_date + timedelta(days=i)
        usage_labels.append(d.strftime('%d/%m'))
        usage_counts.append(trend_dict.get(d, 0))
 
    # 2. Revenue History (For the selected range)
    revenue_trend_data = tx_filtered \
        .annotate(day=TruncDate('created_at')) \
        .values('day') \
        .annotate(total=Sum('amount')) \
        .order_by('day')
    
    revenue_history_labels = []
    revenue_history_amounts = []
    rev_dict = {item['day']: float(item['total']) for item in revenue_trend_data}
    for i in range(delta + 1):
        d = start_date + timedelta(days=i)
        revenue_history_labels.append(d.strftime('%d/%m'))
        revenue_history_amounts.append(rev_dict.get(d, 0))
 
    is_super = super_admin_only(request.user)
    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_users': total_users,
        'new_users_in_range': new_users_in_range,
        'free_users': free_users,
        'plus_users': plus_users,
        'premium_users': premium_users,
        'total_ai_calls': total_ai_calls,
        'success_ai_calls': success_ai_calls,
        'ai_success_rate': ai_success_rate,
        'estimated_revenue': estimated_revenue,
        'actual_revenue': actual_revenue,
        'recent_ai_logs': AIUsageLog.objects.all().order_by('-timestamp')[:5],
        'recent_transactions': Transaction.objects.all().order_by('-created_at')[:5],
        'is_super': is_super,
        
        # Chart Data
        'usage_labels': usage_labels,
        'usage_counts': usage_counts,
        'revenue_labels': revenue_history_labels,
        'revenue_amounts': revenue_history_amounts,
    }
    
    # === NEW ACTIONABLE METRICS (Only for Super Admin) ===
    if is_super:
        # 1. Engagement
        total_uploads = FileUploadLog.objects.filter(timestamp__date__range=[start_date, end_date]).count()
        engagement_metrics = {
            'avg_uploads': (total_uploads / total_users) if total_users > 0 else 0,
            'session_depth': 0,
            'avg_ttv': usage_filtered.aggregate(Avg('processing_time'))['processing_time__avg'] or 0,
        }
        user_days = usage_filtered.values('user', 'timestamp__date').distinct().count()
        if user_days > 0:
            engagement_metrics['session_depth'] = total_ai_calls / user_days
        
        # 2. Quality & Trust
        saves_count = UserActionLog.objects.filter(action_type__in=['SAVE_REPORT', 'DOWNLOAD_CHART'], timestamp__date__range=[start_date, end_date]).count()
        corrections_count = usage_filtered.filter(is_correction=True).count()
        negative_feedback_count = usage_filtered.filter(Q(feedback_stars__lte=2) | Q(is_regenerated=True)).count()
        quality_metrics = {
            'acceptance_rate': (saves_count / total_ai_calls * 100) if total_ai_calls > 0 else 0,
            'correction_rate': (corrections_count / total_ai_calls * 100) if total_ai_calls > 0 else 0,
            'negative_loop': (negative_feedback_count / total_ai_calls * 100) if total_ai_calls > 0 else 0,
        }

        # 3. Growth
        exports_shares = UserActionLog.objects.filter(action_type__in=['SHARE_LINK', 'DOWNLOAD_CHART'], timestamp__date__range=[start_date, end_date]).count()
        growth_metrics = {
            'share_rate': (exports_shares / total_ai_calls * 100) if total_ai_calls > 0 else 0,
            'retention_30d': 0,
        }
        active_old_users = usage_filtered.filter(user__date_joined__date__lt=start_date).values('user').distinct().count()
        total_old_users = User.objects.filter(date_joined__date__lt=start_date).count()
        if total_old_users > 0:
            growth_metrics['retention_30d'] = (active_old_users / total_old_users * 100)

        # 4. Technical
        technical_metrics = {
            'success_rate': ai_success_rate,
            'data_token_ratio': usage_filtered.aggregate(Avg('file_size_kb'))['file_size_kb__avg'] or 0,
        }

        # 5. Website Traffic
        total_visits = traffic_filtered.count()
        unique_visitors = traffic_filtered.values('ip_address').distinct().count()
        avg_duration = traffic_filtered.aggregate(Avg('duration_seconds'))['duration_seconds__avg'] or 0
        traffic_stats = {
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'avg_duration_min': round(avg_duration / 60, 1),
        }

        context.update({
            'engagement': engagement_metrics,
            'quality': quality_metrics,
            'growth': growth_metrics,
            'technical': technical_metrics,
            'traffic_stats': traffic_stats,
        })

    if request.GET.get('export') == 'excel':
        # Get permissions for the current user
        is_super = request.user.is_superuser
        admin_perms, _ = AdminPermission.objects.get_or_create(user=request.user)
        
        daily_data = []
        delta = (end_date - start_date).days
        for i in range(delta + 1):
            d = start_date + timedelta(days=i)
            
            # Filter data for this specific day
            usage_day = usage_filtered.filter(timestamp__date=d)
            traffic_day = traffic_filtered.filter(start_time__date=d)
            tx_day = tx_filtered.filter(created_at__date=d)
            
            row = {'Ngày': d.strftime('%Y-%m-%d')}
            
            # User permissions
            if is_super or admin_perms.can_view_users:
                users_count = User.objects.filter(date_joined__date__lte=d).count()
                new_users = User.objects.filter(date_joined__date=d).count()
                row['Tổng User (Tích lũy)'] = users_count
                row['User đăng ký mới'] = new_users
            
            # AI permissions
            if is_super or admin_perms.can_view_ai_logs:
                total_ai = usage_day.count()
                success_ai = usage_day.filter(status='SUCCESS').count()
                ai_rate = (success_ai / total_ai * 100) if total_ai > 0 else 0
                row['Yêu cầu AI (Queries)'] = total_ai
                row['Tỷ lệ AI Thành công (%)'] = round(ai_rate, 1)
            
            # Finance permissions
            if is_super or admin_perms.can_view_finance:
                rev_day = tx_day.aggregate(total=Sum('amount'))['total'] or 0
                row['Doanh thu thực (VNĐ)'] = rev_day
            
            # System permissions
            if is_super or admin_perms.can_view_system:
                visits = traffic_day.count()
                visitors = traffic_day.values('ip_address').distinct().count()
                duration_avg = traffic_day.aggregate(Avg('duration_seconds'))['duration_seconds__avg'] or 0
                row['Lượt truy cập (Visits)'] = visits
                row['Khách duy nhất (Visitors)'] = visitors
                row['TG ở lại trung bình (phút)'] = round(duration_avg / 60, 1)
            
            daily_data.append(row)
            
        return export_to_excel(daily_data, f"Mia_Daily_Analytics_{start_date}_to_{end_date}")
    
    context['is_super'] = request.user.is_superuser
    return render(request, get_template_name(request, 'management/dashboard.html'), context)

@staff_member_required
@admin_permission_required('can_view_users')
def user_management(request, is_super=False):
    q = request.GET.get('search', '').strip()
    users = User.objects.all().select_related('userprofile')
    
    if q:
        search_filter = Q(username__icontains=q) | \
                        Q(email__icontains=q) | \
                        Q(userprofile__first_name__icontains=q) | \
                        Q(userprofile__last_name__icontains=q)
        
        # If searching by Mã KH (yymmdd + ID)
        if q.isdigit() and len(q) >= 7:
            date_part = q[:6]
            id_part = q[6:]
            # We filter by the ID part first (very efficient)
            try:
                users_by_id = User.objects.filter(id=id_part)
                # Then we verify if the date matches in a case where there's a match
                for u in users_by_id:
                    if u.date_joined.strftime('%y%m%d') == date_part:
                        search_filter |= Q(id=u.id)
            except:
                pass
        
        # Also allow searching by plain ID if it's short
        if q.isdigit() and len(q) < 7:
            search_filter |= Q(id=q)

        users = users.filter(search_filter)

    users = users.order_by('-date_joined')
    
    if request.GET.get('export') == 'excel':
        export_data = []
        for u in users:
            profile = getattr(u, 'userprofile', None)
            export_data.append({
                'ID': u.id,
                'Username': u.username,
                'Họ tên': f"{u.first_name} {u.last_name}",
                'Email': u.email,
                'Gói dịch vụ': profile.get_tier_display() if profile else 'N/A',
                'Ngày tham gia': u.date_joined.strftime('%Y-%m-%d %H:%M'),
                'Nhân viên': 'Có' if u.is_staff else 'Không',
                'Trạng thái': 'Hoạt động' if u.is_active else 'Bị khóa'
            })
        return export_to_excel(export_data, f"Mia_User_List_{timezone.now().strftime('%Y%m%d')}")

    permissions_fields = [
        ('can_view_blog', 'Nội dung'),
        ('can_view_users', 'Khách hàng'),
        ('can_view_ai_logs', 'AI Logs'),
        ('can_view_vouchers', 'Voucher'),
        ('can_view_notifications', 'Thông báo'),
        ('can_view_finance', 'Tài chính'),
        ('can_view_system', 'Hệ thống')
    ]

    context = {
        'users': users, 
        'search_query': q, 
        'is_super': is_super,
        'permissions_fields': permissions_fields
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, get_template_name(request, 'management/user_list_partial.html', is_super=is_super), context)
        
    return render(request, get_template_name(request, 'management/users.html', is_super=is_super), context)

@staff_member_required
@user_passes_test(super_admin_only)
def toggle_staff_status(request, user_id):
    user = User.objects.get(id=user_id)
    if user == request.user:
        messages.error(request, "Bạn không thể tự thay đổi quyền của chính mình.")
    else:
        user.is_staff = not user.is_staff
        user.save()
        messages.success(request, f"Đã cập nhật quyền Staff cho {user.username}.")
    
    redirect_url = 'super_user_management' if request.user.is_superuser else 'user_management'
    return redirect(redirect_url)

@user_passes_test(super_admin_only)
def update_user_tier(request, user_id):
    if request.method == 'POST':
        new_tier = request.POST.get('tier')
        profile = UserProfile.objects.get(user_id=user_id)
        profile.tier = new_tier
        profile.save()
        messages.success(request, f"Đã cập nhật gói dịch vụ cho {profile.user.username} thành {profile.get_tier_display()}.")
    
    redirect_url = 'super_user_management' if request.user.is_superuser else 'user_management'
    return redirect(redirect_url)

@staff_member_required
@admin_permission_required('can_view_ai_logs')
def ai_usage_stats(request, is_super=False):
    logs = AIUsageLog.objects.all().order_by('-timestamp')
    model_stats = AIUsageLog.objects.values('model_name').annotate(count=Count('id'), total_tokens=Sum('total_tokens'))
    return render(request, get_template_name(request, 'management/ai_logs.html', is_super=is_super), {'logs': logs, 'model_stats': model_stats, 'is_super': is_super})

@staff_member_required
@admin_permission_required('can_view_vouchers')
def voucher_management(request, is_super=False):
    vouchers = Voucher.objects.all().order_by('-created_at')
    return render(request, get_template_name(request, 'management/vouchers.html', is_super=is_super), {'vouchers': vouchers, 'is_super': is_super})

@staff_member_required
def create_voucher(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        voucher_type = request.POST.get('voucher_type')
        discount_val = request.POST.get('discount_val')
        max_uses = request.POST.get('max_uses', 1)
        
        if not discount_val:
            discount_val = None
            
        Voucher.objects.create(
            code=code,
            voucher_type=voucher_type,
            discount_val=discount_val,
            max_uses=max_uses
        )
        messages.success(request, f"Đã tạo voucher {code} thành công!")
    
    redirect_url = 'super_voucher_management' if request.user.is_superuser else 'voucher_management'
    return redirect(redirect_url)
from accounts.models import UserProfile, Transaction, Voucher, VoucherUsage, Notification

@staff_member_required
@admin_permission_required('can_view_notifications')
def notification_management(request, is_super=False):
    if request.method == 'POST':
        title = request.POST.get('title')
        message = request.POST.get('message')
        target_group = request.POST.get('target_group')
        link = request.POST.get('link')
        
        users_to_notify = User.objects.all()
        if target_group != 'ALL':
            users_to_notify = User.objects.filter(userprofile__tier=target_group)
            
        notifications = [
            Notification(user=user, title=title, message=message, link=link)
            for user in users_to_notify
        ]
        Notification.objects.bulk_create(notifications)
        
        messages.success(request, f"Đã gửi thông báo tới {len(notifications)} người dùng.")
        redirect_url = 'super_notification_management' if is_super else 'notification_management'
        return redirect(redirect_url)

    # Stats
    total_users = User.objects.count()
    expiring_users = UserProfile.objects.filter(
        subscription_end_date__range=[timezone.now(), timezone.now() + timedelta(days=7)]
    ).count()
    total_notifications_sent = Notification.objects.count()
    
    context = {
        'total_users': total_users,
        'expiring_users': expiring_users,
        'total_notifications_sent': total_notifications_sent,
        'is_super': is_super,
    }
    return render(request, get_template_name(request, 'management/notifications.html', is_super=is_super), context)


# ===== FINANCE MODULE =====

@staff_member_required
@admin_permission_required('can_view_finance')
def finance_dashboard(request, is_super=False):
    today = datetime.now().date()
    start_date_str = request.GET.get('start_date')
    end_date_str   = request.GET.get('end_date')

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        end_date = today

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        # Default: first day of current month
        start_date = today.replace(day=1)

    # --- INCOME: Successful transactions in range ---
    tx_qs = Transaction.objects.filter(
        status='SUCCESS',
        created_at__date__range=[start_date, end_date]
    ).order_by('-created_at')
    total_income = tx_qs.aggregate(total=Sum('amount'))['total'] or 0

    # --- EXPENSES: PlatformExpense in range ---
    expense_qs = PlatformExpense.objects.filter(
        expense_date__range=[start_date, end_date]
    )
    total_expense = expense_qs.aggregate(total=Sum('amount'))['total'] or 0
    profit = total_income - total_expense

    # --- Chart data: daily income vs expense ---
    delta = (end_date - start_date).days
    chart_labels = []
    chart_income = []
    chart_expense = []

    # Safe aggregation using Python for SQLite compatibility
    income_by_day = {}
    for tx in tx_qs:
        d = tx.created_at.date()
        income_by_day[d] = income_by_day.get(d, 0) + float(tx.amount)

    expense_by_day = {}
    for exp in expense_qs:
        d = exp.expense_date # This is already a date field
        expense_by_day[d] = expense_by_day.get(d, 0) + float(exp.amount)

    chart_profit = []

    for i in range(delta + 1):
        d = start_date + timedelta(days=i)
        chart_labels.append(d.strftime('%d/%m'))
        inc = income_by_day.get(d, 0)
        exp = expense_by_day.get(d, 0)
        chart_income.append(inc)
        chart_expense.append(exp)
        chart_profit.append(inc - exp)

    # --- Category breakdown ---
    cat_dict = dict(PlatformExpense.CATEGORY_CHOICES)
    category_data = expense_qs.values('category').annotate(total=Sum('amount')).order_by('-total')
    category_labels = [cat_dict.get(c['category'], c['category']) for c in category_data]
    category_amounts = [float(c['total']) for c in category_data]

    # --- Handle Excel export ---
    if request.GET.get('export') == 'excel':
        rows = []
        # Income rows
        for tx in tx_qs:
            rows.append({
                'Ngày': tx.created_at.strftime('%Y-%m-%d'),
                'Loại': 'THU',
                'Danh mục': f"Đăng ký {tx.tier_requested}",
                'Mô tả': f"Ref: {tx.reference_code} | User: {tx.user.username}",
                'Số tiền (VNĐ)': float(tx.amount),
                'Ghi chú': '',
            })
        # Expense rows
        for exp in expense_qs:
            rows.append({
                'Ngày': exp.expense_date.strftime('%Y-%m-%d'),
                'Loại': 'CHI',
                'Danh mục': cat_dict.get(exp.category, exp.category),
                'Mô tả': exp.title,
                'Số tiền (VNĐ)': float(exp.amount),
                'Ghi chú': exp.note,
            })
        rows.sort(key=lambda x: x['Ngày'])
        return export_to_excel(rows, f"Mia_Finance_{start_date}_to_{end_date}")

    context = {
        'is_super': is_super,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_income': total_income,
        'total_expense': total_expense,
        'profit': profit,
        'transactions': tx_qs,
        'expenses': expense_qs,
        'chart_labels': json.dumps(chart_labels),
        'chart_income': json.dumps(chart_income),
        'chart_expense': json.dumps(chart_expense),
        'chart_profit': json.dumps(chart_profit),
        'category_labels': json.dumps(category_labels),
        'category_amounts': json.dumps(category_amounts),
        'expense_categories': PlatformExpense.CATEGORY_CHOICES,
    }
    return render(request, get_template_name(request, 'management/finance.html', is_super=is_super), context)


@staff_member_required
def add_expense(request):
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        category    = request.POST.get('category', 'OTHER')
        amount_str  = request.POST.get('amount', '0').replace(',', '').strip()
        note        = request.POST.get('note', '').strip()
        expense_date_str = request.POST.get('expense_date', '')

        try:
            amount = int(float(amount_str))
            expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
            PlatformExpense.objects.create(
                title=title,
                category=category,
                amount=amount,
                note=note,
                expense_date=expense_date,
                created_by=request.user,
            )
            messages.success(request, f'✅ Đã thêm khoản chi "{title}" — {amount:,}đ')
        except Exception as e:
            messages.error(request, f'❌ Lỗi: {e}')

    redirect_url = 'super_finance_dashboard' if request.user.is_superuser else 'finance_dashboard'
    return redirect(redirect_url)


@staff_member_required
def delete_expense(request, expense_id):
    if request.method == 'POST':
        exp = get_object_or_404(PlatformExpense, id=expense_id)
        name = exp.title
        exp.delete()
        messages.success(request, f'Đã xoá khoản chi "{name}".')
    return redirect('finance_dashboard')
@user_passes_test(super_admin_only)
def permissions_management(request):
    # Chỉ hiển thị những người là Staff hoặc Superuser
    users = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).select_related('userprofile', 'admin_permission').order_by('-is_superuser', '-is_staff', 'username')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        target_user = get_object_or_404(User, id=user_id)
        
        if action == 'toggle_staff':
            target_user.is_staff = not target_user.is_staff
            target_user.save()
            messages.success(request, f"Đã cập nhật quyền Staff cho {target_user.username}")
        elif action == 'toggle_superuser':
            target_user.is_superuser = not target_user.is_superuser
            target_user.save()
            messages.success(request, f"Đã cập nhật quyền Superuser cho {target_user.username}")
        elif action == 'toggle_permission':
            permission_field = request.POST.get('permission_field')
            perms, _ = AdminPermission.objects.get_or_create(user=target_user)
            current_val = getattr(perms, permission_field)
            setattr(perms, permission_field, not current_val)
            perms.save()
            messages.success(request, f"Đã cập nhật quyền cho {target_user.username}")
        elif action == 'update_role':
            role_title = request.POST.get('role_title', '').strip()
            perms, _ = AdminPermission.objects.get_or_create(user=target_user)
            perms.role_title = role_title
            perms.save()
            messages.success(request, f"Đã cập nhật vị trí cho {target_user.username} thành {role_title}")
        elif action == 'bulk_update_permissions':
            perms, _ = AdminPermission.objects.get_or_create(user=target_user)
            fields = ['can_view_blog', 'can_view_users', 'can_view_ai_logs', 'can_view_vouchers', 
                      'can_view_notifications', 'can_view_finance', 'can_view_system']
            for field in fields:
                setattr(perms, field, request.POST.get(field) == 'on')
            
            # Update role_title
            perms.role_title = request.POST.get('role_title', '').strip()
            perms.save()

            # Update staff/superuser status if provided in form
            if 'is_staff' in request.POST or action == 'bulk_update_permissions':
                target_user.is_staff = request.POST.get('is_staff') == 'on'
            if 'is_superuser' in request.POST or action == 'bulk_update_permissions':
                target_user.is_superuser = request.POST.get('is_superuser') == 'on'
            target_user.save()

            messages.success(request, f"Đã cập nhật toàn bộ quyền & vị trí cho {target_user.username}")
            
        next_url = request.POST.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('permissions_management')

    return render(request, get_template_name(request, 'management/permissions.html', is_super=True), {'users': users, 'is_super': True})

@user_passes_test(super_admin_only)
def super_ai_chat(request):
    return render(request, get_template_name(request, 'management/ai_chat.html', is_super=True), {'is_super': True})

@user_passes_test(super_admin_only)
@admin_permission_required('can_view_system')
def system_management(request):
    connectors = list(DatabaseCredential.objects.all().select_related('user')) + \
                list(ApiCredential.objects.all().select_related('user'))
    workflows = ELTWorkflow.objects.all().select_related('user')
    
    context = {
        'connectors': connectors,
        'workflows': workflows,
        'is_super': True,
    }
    return render(request, get_template_name(request, 'management/system.html', is_super=True), context)

# --- Mia Control: Super Admin Versions ---

@user_passes_test(super_admin_only)
def super_user_management(request):
    return user_management(request, is_super=True)

@user_passes_test(super_admin_only)
def super_ai_usage_stats(request):
    return ai_usage_stats(request, is_super=True)

@user_passes_test(super_admin_only)
def super_voucher_management(request):
    return voucher_management(request, is_super=True)

@user_passes_test(super_admin_only)
def super_notification_management(request):
    return notification_management(request, is_super=True)

@user_passes_test(super_admin_only)
def super_finance_dashboard(request):
    return finance_dashboard(request, is_super=True)

@user_passes_test(super_admin_only)
def analyze_workflow_intelligence(request, workflow_id):
    """API cho Super Admin: AI phân tích sâu hiệu suất của một Workflow."""
    workflow = get_object_or_404(ELTWorkflow, id=workflow_id)
    # pyrefly: ignore [missing-attribute]
    logs = ELTPipelineLog.objects.filter(workflow=workflow).order_by('-start_time')[:20]
    
    log_data = []
    success_count = 0
    for l in logs:
        duration = 0
        if l.end_time:
            duration = (l.end_time - l.start_time).total_seconds()
        log_data.append({
            "status": l.status,
            "duration": duration,
            "error": l.error_message[:100] if l.error_message else ""
        })
        if l.status == 'SUCCESS':
            success_count += 1
            
    success_rate = (success_count / len(logs) * 100) if logs else 0
    
    system_prompt = f"""You are a Pipeline Optimization AI. Analyze this workflow's performance data.
    WORKFLOW: {workflow.name}
    OWNER: {workflow.user.username}
    INTENT: {workflow.user_intent}
    STATS (Last 20 runs): {len(logs)} runs, {success_rate:.1f}% success rate.
    LOG DETAILS: {json.dumps(log_data)}
    
    STRICT RULES:
    1. Respond in Vietnamese.
    2. Format using <h3>, <h4>, <p>, <div class="insight-box">.
    3. Be critical: if logs show failures or high duration, point them out.
    4. Provide strategic advice for the Founder to optimize the system."""

    try:
        from analytics.ai_utils import get_generative_model
        ai_model = get_generative_model()
        response = ai_model.generate_content(system_prompt)
        return JsonResponse({"html": response.text})
    except Exception as e:
        return JsonResponse({"html": f"<p class='text-rose-500'>Lỗi AI: {str(e)}</p>"}, status=500)
