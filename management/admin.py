from django.contrib import admin
from .models import SecurityLog, SalesLead

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt_preview', 'is_malicious', 'timestamp')
    list_filter = ('is_malicious', 'timestamp')
    search_fields = ('user__username', 'prompt', 'analysis_reason')
    readonly_fields = ('timestamp',)

    def prompt_preview(self, obj):
        return obj.prompt[:50] + "..." if len(obj.prompt) > 50 else obj.prompt
    prompt_preview.short_description = "Nội dung câu hỏi"

@admin.register(SalesLead)
class SalesLeadAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'info_preview', 'updated_at')
    search_fields = ('session_id', 'user__username', 'collected_info')
    readonly_fields = ('session_id', 'chat_history', 'created_at', 'updated_at')

    def info_preview(self, obj):
        import json
        return json.dumps(obj.collected_info, ensure_ascii=False)[:100]
    info_preview.short_description = "Thông tin thu thập"
