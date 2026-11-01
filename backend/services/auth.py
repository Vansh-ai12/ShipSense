import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError



SECRET_KEY = os.environ["JWT_SECRET"]       
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

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