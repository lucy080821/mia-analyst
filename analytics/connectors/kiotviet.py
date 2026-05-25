import pandas as pd
import requests
from .base import BaseApiConnector

class KiotVietConnector(BaseApiConnector):
    """
    Connector for KiotViet API.
    Uses client_id and client_secret (stored in api_key_enc) to get an access token.
    """
    
    def __init__(self, credential_instance):
        super().__init__(credential_instance)
        # KiotViet usually uses the Retailer (Name) as part of the URL, so we can store it in 'name'
        self.retailer = self.credential.name
        self.base_url = f"https://public.kiotapi.com"
        self.token = None

    def _get_access_token(self) -> str:
        """Fetches a new access token using client_id and client_secret."""
        token_url = f"https://id.kiotviet.vn/connect/token"
        payload = {
            'scopes': 'PublicApi.Access',
            'grant_type': 'client_credentials',
            'client_id': self.credential.client_id,
            'client_secret': self.api_key
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(token_url, data=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        else:
            raise Exception(f"Failed to get KiotViet token: {response.text}")

    def test_connection(self) -> tuple[bool, str]:
        try:
            self.token = self._get_access_token()
            return True, "Kết nối KiotViet thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối KiotViet: {str(e)}"

    def extract_to_dataframe(self, endpoint: str = 'invoices', params: dict = None, **kwargs) -> pd.DataFrame:
        """
        Extract data from a specific KiotViet endpoint.
        Common endpoints: 'invoices', 'orders', 'products'.
        """
        if not self.token:
            self.token = self._get_access_token()
            
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Retailer': self.retailer
        }
        
        all_data = []
        current_params = params or {}
        # Pagination handling
        current_params.setdefault('pageSize', 100)
        
        # Simple loop for fetching a few pages (for full ELT, this should be more robust)
        try:
            response = requests.get(url, headers=headers, params=current_params)
            response.raise_for_status()
            data = response.json()
            
            # KiotViet typically returns data in a 'data' array
            records = data.get('data', [])
            if records:
                all_data.extend(records)
                
            if not all_data:
                return pd.DataFrame()
                
            return pd.json_normalize(all_data)
            
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ KiotViet API: {str(e)}")
