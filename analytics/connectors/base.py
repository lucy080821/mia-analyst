import pandas as pd
from abc import ABC, abstractmethod
from analytics.models import DatabaseCredential, ApiCredential
import os
from cryptography.fernet import Fernet
from django.conf import settings

def get_cipher():
    """Returns a Fernet cipher instance based on the settings ENCRYPTION_KEY."""
    return Fernet(settings.ENCRYPTION_KEY)

class BaseConnector(ABC):
    """
    Abstract base class for all data connectors (DB, API, etc.)
    Every connector must be able to test its connection and extract data to a DataFrame.
    """
    
    def __init__(self, credential_instance):
        self.credential = credential_instance
        self.cipher = get_cipher()

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Tests the connection. Returns (True, "Success message") or (False, "Error message")."""
        pass

    @abstractmethod
    def extract_to_dataframe(self, **kwargs) -> pd.DataFrame:
        """Extracts data and returns it as a Pandas DataFrame."""
        pass

class BaseDatabaseConnector(BaseConnector):
    """
    Base class specifically for relational database connectors (MySQL, Postgres, etc.)
    """
    
    def __init__(self, credential_instance: DatabaseCredential):
        super().__init__(credential_instance)
        
    @property
    def password(self) -> str:
        """Decrypts and returns the database password."""
        if hasattr(self, '_password_override'):
            return self._password_override
        return self.cipher.decrypt(self.credential.password_enc.encode()).decode()

    @password.setter
    def password(self, value):
        self._password_override = value

    @abstractmethod
    def get_connection_string(self) -> str:
        """Constructs the SQLAlchemy connection string."""
        pass

class BaseApiConnector(BaseConnector):
    """
    Base class specifically for API connectors (KiotViet, Facebook Ads, etc.)
    """
    
    def __init__(self, credential_instance: ApiCredential):
        super().__init__(credential_instance)
        
    @property
    def api_key(self) -> str:
        """Decrypts and returns the API key/secret."""
        return self.cipher.decrypt(self.credential.api_key_enc.encode()).decode()
