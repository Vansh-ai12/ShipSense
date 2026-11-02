import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from db.models import RefreshToken
from db.engine import get_session

import hashlib

from sqlmodel import Session

SECRET_KEY = os.environ["JWT_SECRET"]       
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def hash_password(plain: str) -> str:
    _ph = PasswordHasher()
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    _ph = PasswordHasher()
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,                        
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:             
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": payload["sub"], "role": payload.get("role")}


def require_roles(*allowed: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return checker


def create_refresh_token(user_id: str , session:Session ) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_DAYS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    expires_at = now + timedelta(days=REFRESH_TOKEN_DAYS)

    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=expires_at,
    )
    try:
        session.add(refresh_token)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create refresh token")
    return token