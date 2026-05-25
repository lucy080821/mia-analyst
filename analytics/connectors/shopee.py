import pandas as pd
from .base import BaseApiConnector
from analytics.shopee_service import ShopeeSyncEngine

class ShopeeConnector(BaseApiConnector):
    """
    Adapter connector that wraps the existing ShopeeSyncEngine into the new Connector framework.
    Uses ApiCredential where 'client_id' stores the shop_id.
    """
    
    def __init__(self, credential_instance):
        super().__init__(credential_instance)
        self.shop_id = self.credential.client_id
        # We initialize the existing engine using the user object
        # Note: This assumes the user has a ShopeeCredentials record linked.
        self.engine = ShopeeSyncEngine(self.credential.user)

    def test_connection(self) -> tuple[bool, str]:
        try:
            # get_valid_access_token checks if token is valid and refreshes if needed
            token = self.engine.get_valid_access_token()
            if token:
                return True, "Kết nối Shopee thành công!"
            return False, "Không thể lấy Access Token của Shopee."
        except Exception as e:
            return False, f"Lỗi kết nối Shopee: {str(e)}"

    def extract_to_dataframe(self, days: int = 30, **kwargs) -> pd.DataFrame:
        """
        Extracts recent orders into a DataFrame.
        Since ShopeeSyncEngine saves directly to the DB, we can just fetch from the DB
        or refactor the engine to return DataFrames. For now, we query the local DB.
        """
        try:
            from analytics.models import ShopeeOrder
            from django.utils import timezone
            from datetime import timedelta
            
            # Sync new data first
            self.engine.sync_orders(days=days)
            
            # Extract to DataFrame from our local DB cache
            cutoff_date = timezone.now() - timedelta(days=days)
            orders = ShopeeOrder.objects.filter(
                user=self.credential.user, 
                shop_id=self.shop_id,
                create_time__gte=cutoff_date
            ).values()
            
            df = pd.DataFrame(list(orders))
            return df
            
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ Shopee: {str(e)}")
