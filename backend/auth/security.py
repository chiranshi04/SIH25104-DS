"""
security.py
-----------
Password hashing aur JWT helpers yahan define hote hain.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from backend.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Password ko bcrypt hash mein convert karo."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Plain password ko stored bcrypt hash se verify karo."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    """60 minute configurable expiry ke saath JWT banao."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "role": role, "exp": expires_at}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """JWT validate karke payload return karo."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
