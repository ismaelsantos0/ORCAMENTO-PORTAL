from passlib.context import CryptContext

# PBKDF2 é bem estável em qualquer ambiente (Railway included)
pwd = CryptContext(
    schemes=["pbkdf2_sha256"],
    default="pbkdf2_sha256",
    deprecated="auto",
)

def hash_password(p: str) -> str:
    if p is None:
        p = ""
    return pwd.hash(str(p))

def verify_password(p: str, hashed: str) -> bool:
    try:
        if p is None:
            p = ""
        return pwd.verify(str(p), hashed)
    except Exception:
        return False
