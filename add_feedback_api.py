def add_feedback_view(filepath):
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write('''

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from management.models import UserFeedback

@csrf_exempt
def submit_feedback(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            customer_name = data.get('customer_name', '').strip()
            service_package = data.get('service_package', '').strip()
            content = data.get('content', '').strip()

            if not content:
                return JsonResponse({'success': False, 'error': 'Vui lòng nhập nội dung.'}, status=400)

            feedback = UserFeedback.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name if customer_name else (request.user.username if request.user.is_authenticated else 'Khách'),
                service_package=service_package if service_package else 'Chưa xác định',
                content=content
            )
            return JsonResponse({'success': True, 'message': 'Cảm ơn bạn đã gửi phản hồi!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
''')

def add_feedback_url(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "path('api/submit-feedback/'" not in content:
        # insert after urlpatterns = [
        content = content.replace('urlpatterns = [', "urlpatterns = [\n    path('api/submit-feedback/', views.submit_feedback, name='submit_feedback'),")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

add_feedback_view(r'C:\Leo Harrison\Mia Analyst\analytics\views.py')
add_feedback_url(r'C:\Leo Harrison\Mia Analyst\analytics\urls.py')
print("Added feedback view and url.")
