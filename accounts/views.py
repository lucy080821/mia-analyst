from core.views import get_template_name
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm, UserSignupForm
from .models import UserProfile, Transaction, Voucher, VoucherUsage, Notification
from django.utils import timezone
from datetime import timedelta
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import re

from django.contrib.auth.views import LoginView
from django.urls import reverse

class MiaLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.username == 'leo12121993':
            return reverse('super_admin_dashboard')
        
        # Default logic
        return super().get_success_url()

def register(request):

    if request.user.is_authenticated:
        return redirect('analytics_dashboard')
        
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # UserProfile is usually created via signals, but we update it here
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.first_name = form.cleaned_data.get('first_name')
            profile.last_name = form.cleaned_data.get('last_name')
            profile.email = form.cleaned_data.get('email')
            profile.phone = form.cleaned_data.get('phone')
            profile.gender = form.cleaned_data.get('gender')
            profile.date_of_birth = form.cleaned_data.get('date_of_birth')
            profile.save()
            
            username = form.cleaned_data.get('username')
            messages.success(request, f'Tài khoản {username} đã được tạo thành công!')
            return redirect('login')
    else:
        form = UserSignupForm()
    return render(request, get_template_name(request, 'accounts/register.html'), {'form': form})

@login_required
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Calculate subscription status
    days_left = 0
    if profile.subscription_end_date:
        delta = profile.subscription_end_date - timezone.now()
        days_left = max(0, delta.days)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, get_template_name(request, 'accounts/profile.html'), {
        'form': form,
        'profile': profile,
        'days_left': days_left
    })

@csrf_exempt
@login_required
def update_profile_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            field = data.get("field")
            value = data.get("value")
            
            profile = request.user.userprofile
            
            if field in ['first_name', 'last_name', 'email', 'phone', 'address', 'bio', 'gender', 'date_of_birth']:
                if field == 'email':
                    request.user.email = value
                    request.user.save()
                    profile.email = value
                elif field in ['first_name', 'last_name']:
                    # Update both User and Profile for consistency
                    setattr(request.user, field, value)
                    request.user.save()
                    setattr(profile, field, value)
                else:
                    setattr(profile, field, value)
                
                profile.save()
                return JsonResponse({"message": f"Đã cập nhật {field}!"})
            return JsonResponse({"error": "Invalid field"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def upgrade(request):
    if request.method == 'POST':
        tier_requested = request.POST.get('tier')
        voucher_code = request.POST.get('voucher_code')
        amount = 0
        if tier_requested == 'ADVANCED':
            amount = 499000
        elif tier_requested == 'ENTERPRISE':
            amount = 1990000
        
        voucher = None
        if voucher_code:
            voucher = Voucher.objects.filter(code=voucher_code, is_active=True).first()
            if voucher and voucher.current_uses() < voucher.max_uses and not VoucherUsage.objects.filter(voucher=voucher, user=request.user).exists():
                if voucher.voucher_type == 'FREE_ADVANCED_7_DAYS' and tier_requested == 'ADVANCED':
                    profile = request.user.userprofile
                    profile.tier = 'ADVANCED'
                    now = timezone.now()
                    if profile.subscription_end_date and profile.subscription_end_date > now:
                        profile.subscription_end_date += timedelta(days=7)
                    else:
                        profile.subscription_start_date = now
                        profile.subscription_end_date = now + timedelta(days=7)
                    profile.save()
                    VoucherUsage.objects.create(voucher=voucher, user=request.user)
                    messages.success(request, f"Bạn đã áp dụng mã {voucher_code} để nhận Free 7 Ngày ADVANCED!")
                    return redirect('profile')
                elif voucher.voucher_type == 'DISCOUNT_PERCENT':
                    amount = int(amount * (100 - voucher.discount_val) / 100)
                elif voucher.voucher_type == 'FIXED_DISCOUNT':
                    amount = max(0, amount - voucher.discount_val)

        if amount > 0:
            ref_code = f"MIA{request.user.id}T{uuid.uuid4().hex[:6].upper()}"
            transaction = Transaction.objects.create(
                user=request.user,
                amount=amount,
                tier_requested=tier_requested,
                reference_code=ref_code
            )
            if voucher:
                # Lock voucher usage with this user invoice
                VoucherUsage.objects.create(voucher=voucher, user=request.user)
            return redirect('process_payment', reference_code=ref_code)
        elif amount == 0 and tier_requested in ['ADVANCED', 'ENTERPRISE'] and voucher:
            profile = request.user.userprofile
            profile.tier = tier_requested
            now = timezone.now()
            if profile.subscription_end_date and profile.subscription_end_date > now:
                profile.subscription_end_date += timedelta(days=30)
            else:
                profile.subscription_start_date = now
                profile.subscription_end_date = now + timedelta(days=30)
            profile.save()
            VoucherUsage.objects.create(voucher=voucher, user=request.user)
            messages.success(request, "Nâng cấp hoàn tất bằng Voucher 100%!")
            return redirect('profile')
    context = {
        'lemon_store_url': getattr(settings, 'LEMON_SQUEEZY_STORE_URL', 'your-store.lemonsqueezy.com'),
        'lemon_variant_id': getattr(settings, 'LEMON_SQUEEZY_VARIANT_ID_ADVANCED', 'variant_id'),
    }
    return render(request, get_template_name(request, 'accounts/upgrade.html'), context)

@csrf_exempt
@login_required
def apply_voucher(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            code = data.get("code")
            voucher = Voucher.objects.filter(code=code, is_active=True).first()
            if not voucher:
                return JsonResponse({"error": "Mã voucher không hợp lệ hoặc đã bị khóa."}, status=400)
            if voucher.expires_at and voucher.expires_at < timezone.now():
                return JsonResponse({"error": "Mã voucher đã hết hạn."}, status=400)
            if voucher.current_uses() >= voucher.max_uses:
                return JsonResponse({"error": "Mã voucher đã hết lượt sử dụng."}, status=400)
            if VoucherUsage.objects.filter(voucher=voucher, user=request.user).exists():
                return JsonResponse({"error": "Bạn đã sử dụng mã này rồi."}, status=400)
            return JsonResponse({
                "message": "Áp dụng thành công",
                "voucher_type": voucher.voucher_type,
                "discount_val": voucher.discount_val
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

import hmac
import hashlib
from django.conf import settings

@login_required
def process_payment(request, reference_code):
    transaction = get_object_or_404(Transaction, reference_code=reference_code, user=request.user)
    
    # Construct payment data for PayOS
    order_code = transaction.id
    amount = int(transaction.amount)
    
    # PayOS limits description length
    desc = f"Mia {transaction.tier_requested} {transaction.user.username}"[:25]
    
    from django.urls import reverse
    relative_status_url = reverse('payment_status', kwargs={'reference_code': reference_code})
    return_url = request.build_absolute_uri(relative_status_url)
    cancel_url = request.build_absolute_uri(relative_status_url)
    
    # Calculate signature
    signature_string = f"amount={amount}&cancelUrl={cancel_url}&description={desc}&orderCode={order_code}&returnUrl={return_url}"
    signature = hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode('utf-8'),
        signature_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    data = {
        "orderCode": order_code,
        "amount": amount,
        "description": desc,
        "returnUrl": return_url,
        "cancelUrl": cancel_url,
        "signature": signature
    }
    
    headers = {
        "x-client-id": settings.PAYOS_CLIENT_ID,
        "x-api-key": settings.PAYOS_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        import requests
        response = requests.post("https://api-merchant.payos.vn/v2/payment-requests", json=data, headers=headers)
        response_data = response.json()
        
        if response_data.get("code") == "00":
            checkout_url = response_data["data"]["checkoutUrl"]
            return redirect(checkout_url)
        else:
            messages.error(request, f"Lỗi tạo thanh toán: {response_data.get('desc')}")
            return redirect('profile')
            
    except Exception as e:
        messages.error(request, f"Lỗi kết nối PayOS: {str(e)}")
        return redirect('profile')

@login_required
def payment_status(request, reference_code):
    transaction = get_object_or_404(Transaction, reference_code=reference_code, user=request.user)
    return JsonResponse({'status': transaction.status})

@csrf_exempt
def payos_webhook(request):
    """
    Webhook endpoint cho PayOS
    """
    if request.method != 'POST':
        return JsonResponse({"error": 1, "message": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        
        # PayOS wraps the webhook data inside 'data' and provides a 'signature' at root
        if "data" not in data or "signature" not in data:
            return JsonResponse({"error": 1, "message": "Invalid format"}, status=400)
            
        webhook_data = data["data"]
        received_signature = data["signature"]
        
        # Verify signature according to PayOS docs
        # Sort keys of webhook_data alphabetically
        sorted_keys = sorted(webhook_data.keys())
        sign_strings = []
        for key in sorted_keys:
            val = webhook_data[key]
            # PayOS docs state to ignore None/Null values or lists/dicts, but typically primitive types are stringified.
            if val is not None and not isinstance(val, (dict, list)):
                sign_strings.append(f"{key}={val}")
                
        signature_string = "&".join(sign_strings)
        calculated_signature = hmac.new(
            settings.PAYOS_CHECKSUM_KEY.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_signature != received_signature:
            return JsonResponse({"error": 1, "message": "Invalid signature"}, status=401)
            
        # Process payment
        # The webhook returns code "00" for success
        if data.get("code") == "00":
            order_code = webhook_data.get("orderCode")
            amount_in = webhook_data.get("amount", webhook_data.get("amountIn", 0)) # handle variations
            
            # Find transaction by orderCode (which is our Transaction ID)
            db_transaction = Transaction.objects.filter(
                id=order_code, 
                status='PENDING'
            ).first()
            
            if db_transaction and int(db_transaction.amount) <= amount_in:
                db_transaction.status = 'SUCCESS'
                db_transaction.save()
                
                # Upgrade/Extend User Subscription
                profile = db_transaction.user.userprofile
                profile.tier = db_transaction.tier_requested
                
                now = timezone.now()
                if profile.subscription_end_date and profile.subscription_end_date > now:
                    profile.subscription_end_date += timedelta(days=30)
                else:
                    profile.subscription_start_date = now
                    profile.subscription_end_date = now + timedelta(days=30)
                
                profile.save()
                return JsonResponse({"error": 0, "message": "Ok", "success": True})
        
        return JsonResponse({"error": 0, "message": "Ignored or non-success code"})
    except Exception as e:
        return JsonResponse({"error": 1, "message": str(e)}, status=400)

@csrf_exempt
def payment_webhook(request):
    """
    Webhook endpoint for Casso.vn or SePay.vn to automate payment detection.
    """
    if request.method != 'POST':
        return JsonResponse({"error": 1, "message": "Invalid method"}, status=405)

    # Security check: You should set 'MIA_SECRET_2024' as the Secure Token in Casso dashboard
    secure_token = request.headers.get('Secure-Token') or request.headers.get('Authorization')
    if secure_token != 'MIA_SECRET_2024':
        # If no token provided or mismatched, reject the request
        return JsonResponse({"error": 1, "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        transactions = data.get('data', [])
        
        processed_count = 0
        for txn in transactions:
            description = txn.get('description', '')
            amount = txn.get('amount', 0)
            
            # Extract Reference Code using Regex (Pattern: MIA[ID]T[HEX])
            match = re.search(r'MIA\d+T[A-Z0-9]+', description, re.IGNORECASE)
            if match:
                ref_code = match.group().upper()
                
                # Find the pending transaction matching code and amount
                db_transaction = Transaction.objects.filter(
                    reference_code=ref_code, 
                    status='PENDING',
                    amount=amount
                ).first()
                
                if db_transaction:
                    db_transaction.status = 'SUCCESS'
                    db_transaction.save()
                    
                    # Upgrade/Extend User Subscription
                    profile = db_transaction.user.userprofile
                    profile.tier = db_transaction.tier_requested
                    
                    # Cumulative extension logic: add 30 days to existing end date if active
                    now = timezone.now()
                    if profile.subscription_end_date and profile.subscription_end_date > now:
                        profile.subscription_end_date += timedelta(days=30)
                    else:
                        profile.subscription_start_date = now
                        profile.subscription_end_date = now + timedelta(days=30)
                    
                    profile.save()
                    processed_count += 1
                    
        return JsonResponse({"error": 0, "message": f"Processed {processed_count} transactions"})
    except Exception as e:
        return JsonResponse({"error": 1, "message": str(e)}, status=400)
# trigger reload

@csrf_exempt
def lemon_squeezy_webhook(request):
    """
    Webhook endpoint for Lemon Squeezy to process successful payments.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        # Verify Signature
        secret = getattr(settings, 'LEMON_SQUEEZY_WEBHOOK_SECRET', 'test_secret')
        signature = request.headers.get('X-Signature', '')
        
        digest = hmac.new(
            secret.encode('utf-8'),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(digest, signature) and secret != 'test_secret':
            return JsonResponse({"error": "Invalid signature"}, status=401)

        payload = json.loads(request.body)
        meta = payload.get('meta', {})
        event_name = meta.get('event_name', '')
        
        if event_name in ['order_created', 'subscription_created']:
            custom_data = meta.get('custom_data', {})
            user_id = custom_data.get('user_id')
            
            if user_id:
                from django.contrib.auth.models import User
                user = User.objects.filter(id=user_id).first()
                if user:
                    profile = user.userprofile
                    profile.tier = 'ADVANCED'
                    
                    now = timezone.now()
                    if profile.subscription_end_date and profile.subscription_end_date > now:
                        profile.subscription_end_date += timedelta(days=30)
                    else:
                        profile.subscription_start_date = now
                        profile.subscription_end_date = now + timedelta(days=30)
                    
                    profile.save()
                    return JsonResponse({"status": "success", "message": "Subscription updated"})
                    
        return JsonResponse({"status": "ignored", "message": f"Event {event_name} ignored"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def mark_notification_read(request, notif_id):
    if request.method == "POST":
        try:
            notif = getattr(request.user, 'notifications').get(id=notif_id)
            notif.is_read = True
            notif.save()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def mark_all_notifications_read(request):
    if request.method == "POST":
        getattr(request.user, 'notifications').filter(is_read=False).update(is_read=True)
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Method not allowed"}, status=405)
@login_required
def notifications_list(request):
    notifs = getattr(request.user, 'notifications').all()
    return render(request, get_template_name(request, 'accounts/notifications.html'), {'notifications': notifs})
