from django import template

register = template.Library()

@register.simple_tag
def define_perms(p, u):
    return [
        {
            'field': 'can_view_blog',
            'label': 'Content',
            'active': p.can_view_blog,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_users',
            'label': 'Customers',
            'active': p.can_view_users,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_ai_logs',
            'label': 'API Logs',
            'active': p.can_view_ai_logs,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_vouchers',
            'label': 'Vouchers',
            'active': p.can_view_vouchers,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_notifications',
            'label': 'Notifications',
            'active': p.can_view_notifications,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_finance',
            'label': 'Finance',
            'active': p.can_view_finance,
            'active_class': 'bg-rose-600 border-rose-600 text-white shadow-lg shadow-rose-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-rose-400 hover:text-rose-500',
        },
        {
            'field': 'can_view_system',
            'label': 'System',
            'active': p.can_view_system,
            'active_class': 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-blue-400 hover:text-blue-500',
        },
    ]

@register.simple_tag
def define_perms_vi(p, u):
    return [
        {
            'field': 'can_view_blog',
            'label': 'Nội dung',
            'active': p.can_view_blog,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_users',
            'label': 'Khách hàng',
            'active': p.can_view_users,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_ai_logs',
            'label': 'API Logs',
            'active': p.can_view_ai_logs,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_vouchers',
            'label': 'Vouchers',
            'active': p.can_view_vouchers,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_notifications',
            'label': 'Thông báo',
            'active': p.can_view_notifications,
            'active_class': 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-indigo-400 hover:text-indigo-500',
        },
        {
            'field': 'can_view_finance',
            'label': 'Tài chính',
            'active': p.can_view_finance,
            'active_class': 'bg-rose-600 border-rose-600 text-white shadow-lg shadow-rose-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-rose-400 hover:text-rose-500',
        },
        {
            'field': 'can_view_system',
            'label': 'Hệ thống',
            'active': p.can_view_system,
            'active_class': 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-500/30',
            'inactive_class': 'bg-white border-slate-200 text-slate-400 hover:border-blue-400 hover:text-blue-500',
        },
    ]
