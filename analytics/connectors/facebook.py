import pandas as pd
import requests
from .base import BaseApiConnector

class FacebookAdsConnector(BaseApiConnector):
    """
    Connector for Facebook Ads Graph API.
    Uses an access token (stored in api_key_enc).
    The 'client_id' field can be used to store the Ad Account ID (e.g., 'act_123456789').
    """
    
    def __init__(self, credential_instance):
        super().__init__(credential_instance)
        self.ad_account_id = self.credential.client_id
        # Default Graph API version, consider making this configurable
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def test_connection(self) -> tuple[bool, str]:
        """Test if the access token is valid by hitting the 'me' endpoint or ad account."""
        url = f"{self.base_url}/{self.ad_account_id}" if self.ad_account_id else f"{self.base_url}/me"
        params = {'access_token': self.api_key}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return True, "Kết nối Facebook Ads thành công!"
            else:
                return False, f"Lỗi xác thực Facebook: {response.json().get('error', {}).get('message', 'Unknown error')}"
        except Exception as e:
            return False, f"Lỗi kết nối API: {str(e)}"

    def extract_to_dataframe(self, endpoint: str = 'insights', params: dict = None, **kwargs) -> pd.DataFrame:
        """
        Extract data from Facebook Ads Insights API.
        Default fetches insights for the configured Ad Account.
        """
        if not self.ad_account_id:
            raise ValueError("Cần cung cấp Ad Account ID (lưu trong client_id) để lấy báo cáo.")
            
        url = f"{self.base_url}/{self.ad_account_id}/{endpoint}"
        
        current_params = params or {}
        current_params['access_token'] = self.api_key
        
        # Default basic fields for Ads reporting
        if 'fields' not in current_params:
            current_params['fields'] = 'date_start,date_stop,campaign_name,impressions,clicks,spend'
        
        all_data = []
        
        try:
            while url:
                response = requests.get(url, params=current_params)
                response.raise_for_status()
                data = response.json()
                
                records = data.get('data', [])
                all_data.extend(records)
                
                # Pagination handling
                paging = data.get('paging', {})
                url = paging.get('next')
                # Clear params on subsequent requests as the 'next' URL already contains them
                current_params = {}
                
            if not all_data:
                return pd.DataFrame()
                
            df = pd.json_normalize(all_data)
            # Basic casting
            if 'spend' in df.columns:
                df['spend'] = pd.to_numeric(df['spend'])
            if 'impressions' in df.columns:
                df['impressions'] = pd.to_numeric(df['impressions'])
            if 'clicks' in df.columns:
                df['clicks'] = pd.to_numeric(df['clicks'])
                
            return df
            
        except requests.exceptions.RequestException as e:
            err_msg = str(e)
            if e.response is not None:
                err_msg = e.response.json().get('error', {}).get('message', str(e))
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ Facebook Ads: {err_msg}")
