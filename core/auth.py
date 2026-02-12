import os
import hmac
import hashlib
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    try:
        return pwd.verify(p, hashed)
    except Exception:
        return False

def sign_token(raw: str) -> str:
    secret = os.getenv("APP_SECRET", "dev-secret")
    mac = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return mac

def safe_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")
