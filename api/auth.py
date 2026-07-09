"""
JWT tabanlı kimlik doğrulama.

Akış:
  1. POST /auth/token  →  username + password → JWT token
  2. Korumalı endpoint  →  Authorization: Bearer <token>  →  get_current_user doğrular

Production'da DEMO_USERS yerine veritabanı kullanılır.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY     = os.environ.get("JWT_SECRET_KEY", "dev-insecure-secret-change-in-production")
ALGORITHM      = os.environ.get("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

# bcrypt ile şifre hash'leme — md5/sha256 yerine bcrypt: brute-force'a karşı dayanıklı
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Swagger UI'da "Authorize" butonu için — token'ı Bearer olarak gönder
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Demo kullanıcılar — production'da Django'nun auth tablosundan gelir
# Şifre: teamsec2024
DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("teamsec2024"),
        "roles": ["admin"],
    },
    "readonly": {
        "username": "readonly",
        "hashed_password": pwd_context.hash("readonly2024"),
        "roles": ["reader"],
    },
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Kullanıcıyı doğrula. Hatalıysa None döner."""
    user = DEMO_USERS.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(username: str) -> str:
    """İmzalı JWT oluştur."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Her korumalı endpoint çalışmadan önce bu fonksiyon çalışır (Depends ile).
    Token geçersizse 401 fırlatır, geçerliyse kullanıcı bilgisini döner.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz veya süresi dolmuş token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc

    user = DEMO_USERS.get(username)
    if not user:
        raise exc
    return user
