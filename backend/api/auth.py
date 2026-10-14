"""
auth.py
-------
Register, login aur authorization test routes yahan hain.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import GENERIC_AUTH_ERROR, get_current_user
from backend.auth.security import create_access_token, hash_password, verify_password
from backend.database.connection import get_db
from backend.database.models import User
from backend.database.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserResponse,
)
from backend.security.rate_limit import enforce_ip_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, http_request: Request, db: Session = Depends(get_db)) -> User:
    """Registration hamesha student role create karti hai."""
    enforce_ip_limit(http_request, "auth-register", 5)
    existing = db.scalar(select(User).where(User.email == request.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        name=request.name,
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        role="student",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email is already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    """Wrong email/password ke liye same generic 401 message do."""
    enforce_ip_limit(http_request, "auth-login", 10)
    user = db.scalar(select(User).where(User.email == request.email.lower()))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail=GENERIC_AUTH_ERROR)

    return LoginResponse(
        access_token=create_access_token(user.id, user.role),
        token_type="bearer",
        user=UserResponse.model_validate(user, from_attributes=True),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user
