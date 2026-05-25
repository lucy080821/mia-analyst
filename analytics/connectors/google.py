import pandas as pd
import requests
import json
from .base import BaseApiConnector

class GoogleConnector(BaseApiConnector):
    """
    Connector for Google APIs (Ads/AdSense).
    Assumes api_key_enc stores a JSON string containing OAuth credentials:
    { "client_id": "...", "client_secret": "...", "refresh_token": "...", "developer_token": "..." }
    """
    
    def __init__(self, credential_instance):
        super().__init__(credential_instance)
        try:
            # Parse the decrypted JSON string to get individual tokens
            self.tokens = json.loads(self.api_key)
        except:
            self.tokens = {"api_key": self.api_key} # Fallback for simple API keys
            
        self.client_id = self.tokens.get('client_id', self.credential.client_id)
        self.access_token = None

    def _refresh_access_token(self):
        """Uses the refresh_token to get a new access_token from Google."""
        url = "https://oauth2.googleapis.com/token"
        payload = {
            'client_id': self.client_id,
            'client_secret': self.tokens.get('client_secret'),
            'refresh_token': self.tokens.get('refresh_token'),
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            self.access_token = response.json().get('access_token')
        else:
            raise Exception(f"Failed to refresh Google token: {response.text}")

    def test_connection(self) -> tuple[bool, str]:
        try:
            if 'refresh_token' in self.tokens:
                self._refresh_access_token()
            return True, "Kết nối Google API thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối Google: {str(e)}"

    def extract_to_dataframe(self, endpoint_url: str, params: dict = None, **kwargs) -> pd.DataFrame:
        """
        Generic extractor for Google REST APIs.
        Example endpoint for AdSense: https://adsense.googleapis.com/v2/accounts/{account}/reports
        """
        if 'refresh_token' in self.tokens and not self.access_token:
            self._refresh_access_token()
            
        headers = {}
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        elif 'api_key' in self.tokens:
            params = params or {}
            params['key'] = self.tokens['api_key']
            
        # For Google Ads API specifically, developer-token is needed
        if 'developer_token' in self.tokens:
            headers['developer-token'] = self.tokens['developer_token']
            
        try:
            response = requests.get(endpoint_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Google APIs often return rows and headers separately for reports
            if 'rows' in data and 'headers' in data:
                columns = [header['name'] for header in data['headers']]
                return pd.DataFrame(data['rows'], columns=columns)
            
            # Or a simple list of items
            for key in ['items', 'data', 'reports']:
                if key in data:
                    return pd.json_normalize(data[key])
                    
            return pd.json_normalize([data])
            
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ Google API: {str(e)}")
