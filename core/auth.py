import os
import hmac
import hashlib
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _normalize_password(p: str) -> str:
    """
    bcrypt tem limite de 72 bytes.
    Se passar disso, converte para SHA-256 hex (64 chars) mantendo segurança.
    """
    if p is None:
        p = ""
    p = str(p)

    b = p.encode("utf-8")
    if len(b) > 72:
        return hashlib.sha256(b).hexdigest()  # 64 chars ASCII
    return p


def hash_password(p: str) -> str:
    p2 = _normalize_password(p)
    return pwd.hash(p2)


def verify_password(p: str, hashed: str) -> bool:
    try:
        p2 = _normalize_password(p)
        return pwd.verify(p2, hashed)
    except Exception:
        return False


def sign_token(raw: str) -> str:
    secret = os.getenv("APP_SECRET", "dev-secret")
    mac = hmac.new(secret.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()
    return mac


def safe_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")
