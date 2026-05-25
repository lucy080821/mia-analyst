def add_clear_history(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    view_code = '''
@login_required
@require_http_methods(["POST"])
@csrf_exempt
def clear_chat_history_api(request):
    try:
        from .models import ChatHistory
        deleted_count, _ = ChatHistory.objects.filter(user=request.user).delete()
        return JsonResponse({'success': True, 'message': 'Đã xóa lịch sử trò chuyện.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
'''
    if 'def clear_chat_history_api' not in content:
        # Append to the end
        content += '\n' + view_code
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

def update_urls(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    url_code = "path('api/chat-history/clear/', views.clear_chat_history_api, name='clear_chat_history_api'),"
    if 'api/chat-history/clear/' not in content:
        content = content.replace("path('api/chat-history/', views.get_chat_history_api, name='get_chat_history_api'),", 
                                  "path('api/chat-history/', views.get_chat_history_api, name='get_chat_history_api'),\n    " + url_code)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

add_clear_history(r'C:\Leo Harrison\Mia Analyst\analytics\views.py')
update_urls(r'C:\Leo Harrison\Mia Analyst\analytics\urls.py')
print("Backend history clear added.")
