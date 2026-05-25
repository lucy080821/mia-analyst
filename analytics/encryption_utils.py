from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    """Returns a Fernet instance using the key from settings."""
    return Fernet(settings.ENCRYPTION_KEY)

def encrypt_token(token: str) -> str:
    """Encrypts a string token and returns the base64 encoded ciphertext."""
    if not token:
        return ""
    f = get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypts a base64 encoded ciphertext and returns the original string."""
    if not encrypted_token:
        return ""
    f = get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()
