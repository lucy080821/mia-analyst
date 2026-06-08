import time
import hmac
import hashlib
import requests
import json
from django.conf import settings
from .encryption_utils import encrypt_token, decrypt_token

class ShopeeBaseService:
    BASE_URL = "https://partner.shopeemobile.com"
    
    @staticmethod
    def generate_sign(path, partner_id, partner_key, timestamp, access_token=None, shop_id=None):
        """
        Generates HMAC-SHA256 signature for Shopee API v2.
        Formula: hmac_sha256(partner_key, path + partner_id + timestamp + [access_token] + [shop_id])
        """
        base_string = f"{partner_id}{path}{timestamp}"
        if access_token:
            base_string += access_token
        if shop_id:
            base_string += str(shop_id)
            
        sign = hmac.new(
            partner_key.encode(),
            base_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return sign

    def call_api(self, path, method="GET", params=None, body=None, access_token=None, shop_id=None):
        """Helper to call Shopee API with mandatory parameters and signature."""
        timestamp = int(time.time())
        partner_id = settings.SHOPEE_PARTNER_ID
        partner_key = settings.SHOPEE_PARTNER_KEY
        
        sign = self.generate_sign(path, partner_id, partner_key, timestamp, access_token, shop_id)
        
        url = f"{self.BASE_URL}{path}"
        common_params = {
            "partner_id": partner_id,
            "timestamp": timestamp,
            "sign": sign
        }
        if access_token:
            common_params["access_token"] = access_token
        if shop_id:
            common_params["shop_id"] = shop_id
            
        if params:
            common_params.update(params)
            
        headers = {"Content-Type": "application/json"}
        
        if method.upper() == "GET":
            response = requests.get(url, params=common_params, headers=headers)
        else:
            response = requests.post(url, params=common_params, json=body, headers=headers)
            
        return response.json()

class ShopeeAuthService(ShopeeBaseService):
    def get_auth_url(self):
        """Generates the URL to redirect user to for Shopee Auth."""
        path = "/api/v2/shop/auth_partner"
        timestamp = int(time.time())
        partner_id = settings.SHOPEE_PARTNER_ID
        partner_key = settings.SHOPEE_PARTNER_KEY
        redirect_url = settings.SHOPEE_REDIRECT_URI
        
        sign = self.generate_sign(path, partner_id, partner_key, timestamp)
        
        auth_url = (
            f"{self.BASE_URL}{path}?"
            f"partner_id={partner_id}&"
            f"timestamp={timestamp}&"
            f"sign={sign}&"
            f"redirect={redirect_url}"
        )
        return auth_url

    def get_tokens(self, code, shop_id):
        """Exchanges auth_code for access_token and refresh_token."""
        path = "/api/v2/auth/token/get"
        body = {
            "code": code,
            "partner_id": settings.SHOPEE_PARTNER_ID,
            "shop_id": int(shop_id)
        }
        # Note: Token exchange API v2 might need sign without access_token and shop_id
        res = self.call_api(path, method="POST", body=body)
        return res

    def refresh_tokens(self, refresh_token, shop_id):
        """Refreshes access_token using refresh_token."""
        path = "/api/v2/auth/access_token/get"
        body = {
            "refresh_token": refresh_token,
            "partner_id": settings.SHOPEE_PARTNER_ID,
            "shop_id": int(shop_id)
        }
        res = self.call_api(path, method="POST", body=body)
        return res

class ShopeeDataService(ShopeeBaseService):
    def get_order_list(self, access_token, shop_id, time_from, time_to, cursor=""):
        """Fetches order list from Shopee."""
        path = "/api/v2/order/get_order_list"
        params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": 20,
            "cursor": cursor
        }
        return self.call_api(path, params=params, access_token=access_token, shop_id=shop_id)

    def get_order_detail(self, access_token, shop_id, order_sn_list):
        """Fetches detailed info for a list of order serial numbers."""
        path = "/api/v2/order/get_order_detail"
        # Optional fields to get more data for EDA
        optional_fields = "buyer_user_id,buyer_username,item_list,recipient_address,actual_shipping_fee,estimated_shipping_fee,payment_method,total_amount,voucher_info,pay_time,order_status"
        params = {
            "order_sn_list": ",".join(order_sn_list),
            "response_optional_fields": optional_fields
        }
        return self.call_api(path, params=params, access_token=access_token, shop_id=shop_id)

    def get_escrow_detail(self, access_token, shop_id, order_sn):
        """Fetches payment/escrow details for an order."""
        path = "/api/v2/payment/get_escrow_detail"
        params = {"order_sn": order_sn}
        return self.call_api(path, params=params, access_token=access_token, shop_id=shop_id)

class ShopeeSyncEngine:
    def __init__(self, user):
        self.user = user
        self.creds = user.shopee_creds
        self.auth_service = ShopeeAuthService()
        self.data_service = ShopeeDataService()

    def get_valid_access_token(self):
        """Checks if token is expired and refreshes if necessary."""
        from django.utils import timezone
        if self.creds.expire_time <= timezone.now():
            refresh_token = decrypt_token(self.creds.refresh_token_enc)
            res = self.auth_service.refresh_tokens(refresh_token, self.creds.shop_id)
            if 'access_token' in res:
                self.creds.access_token_enc = encrypt_token(res['access_token'])
                self.creds.refresh_token_enc = encrypt_token(res['refresh_token'])
                self.creds.expire_time = timezone.now() + timedelta(seconds=res.get('expire_in', 14400))
                self.creds.save()
        return decrypt_token(self.creds.access_token_enc)

    def sync_orders(self, days=15):
        """Fetches and saves orders for the last N days."""
        from django.utils import timezone
        from datetime import timedelta
        from .models import SCMOrder
        
        access_token = self.get_valid_access_token()
        shop_id = self.creds.shop_id
        
        time_to = int(time.time())
        time_from = time_to - (86400 * days)
        
        cursor = ""
        all_order_sns = []
        
        # 1. Get all order SNs
        while True:
            res = self.data_service.get_order_list(access_token, shop_id, time_from, time_to, cursor)
            resp = res.get('response', {})
            orders = resp.get('order_list', [])
            all_order_sns.extend([o['order_sn'] for o in orders])
            
            if resp.get('more'):
                cursor = resp.get('next_cursor')
            else:
                break
        
        # 2. Fetch details and escrow in batches (order_detail supports 50 SNs)
        batch_size = 50
        for i in range(0, len(all_order_sns), batch_size):
            batch = all_order_sns[i:i+batch_size]
            details_res = self.data_service.get_order_detail(access_token, shop_id, batch)
            order_details = details_res.get('response', {}).get('order_list', [])
            
            for detail in order_details:
                order_sn = detail['order_sn']
                
                # Fetch escrow for each order (one by one as per API)
                escrow_res = self.data_service.get_escrow_detail(access_token, shop_id, order_sn)
                escrow = escrow_res.get('response', {})
                
                # Map to model
                create_time = timezone.datetime.fromtimestamp(detail['create_time'], tz=timezone.utc)
                pay_time = None
                if detail.get('pay_time'):
                    pay_time = timezone.datetime.fromtimestamp(detail['pay_time'], tz=timezone.utc)
                
                # Extract financial data
                order_income = escrow.get('order_income', {})
                
                # Update or create order record
                SCMOrder.objects.update_or_create(
                    order_sn=order_sn,
                    defaults={
                        'platform_source': 'shopee',
                        'user': self.user,
                        'shop_id': shop_id,
                        'order_status': detail['order_status'],
                        'create_time': create_time,
                        'pay_time': pay_time,
                        'total_amount': detail.get('total_amount', 0),
                        'actual_shipping_fee': detail.get('actual_shipping_fee', 0),
                        'estimated_shipping_fee': detail.get('estimated_shipping_fee', 0),
                        'escrow_amount': order_income.get('escrow_amount', 0),
                        'service_fee': order_income.get('service_fee', 0),
                        'seller_transaction_fee': order_income.get('seller_transaction_fee', 0),
                        'commission_fee': order_income.get('commission_fee', 0),
                        'seller_rebate': order_income.get('seller_rebate', 0),
                        'platform_rebate': order_income.get('shopee_rebate', 0),
                        'voucher_seller': order_income.get('voucher_seller', 0),
                        'voucher_platform': order_income.get('voucher_shopee', 0),
                        'buyer_username': detail.get('buyer_username'),
                        'payment_method': detail.get('payment_method'),
                    }
                )
        return len(all_order_sns)
