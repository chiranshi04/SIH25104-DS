"""
dependencies.py
---------------
JWT se current user aur role dependencies yahan milti hain.
"""

from collections.abc import Callable
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.security import decode_token
from backend.database.connection import get_db
from backend.database.models import User

GENERIC_AUTH_ERROR = "Invalid authentication credentials"


def _get_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    return token.strip()


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub", ""))
    except Exception:
        # Token errors ko same generic 401 response do.
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR) from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """No token par guest None; token diya ho aur invalid ho toh 401."""
    token = _get_bearer_token(authorization)
    if token is None:
        return None
    return _user_from_token(token, db)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Login-required dependency."""
    token = _get_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    return _user_from_token(token, db)


def require_roles(*allowed_roles: str) -> Callable:
    """Allowed roles ke liye reusable dependency factory."""
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
