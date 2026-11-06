import base64
import hashlib
import hmac
import os


def _key() -> bytes:
    secret = os.getenv("DATA_ENCRYPTION_KEY", "")
    if len(secret) < 32:
        raise RuntimeError("DATA_ENCRYPTION_KEY must be set to encrypt model credentials")
    return hashlib.sha256(secret.encode()).digest()


def encrypt_secret(value: str) -> str:
    from cryptography.fernet import Fernet

    fernet_key = base64.urlsafe_b64encode(_key())
    return Fernet(fernet_key).encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    from cryptography.fernet import Fernet

    fernet_key = base64.urlsafe_b64encode(_key())
    return Fernet(fernet_key).decrypt(value.encode()).decode()


def mask_secret(value: str) -> str:
    return "••••••••" + value[-4:] if len(value) > 4 else "••••"
