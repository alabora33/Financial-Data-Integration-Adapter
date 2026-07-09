"""
JWT tabanlı + API Key kimlik doğrulama.

İki yöntem desteklenir:
  1. Bearer JWT  → POST /auth/token'dan alınan token
  2. API Key     → X-API-Key header (ortam değişkeni ile yönetilir)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-secret-change-in-production")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

_raw_keys = os.environ.get("API_KEYS", "teamsec-dev-key:admin")
API_KEYS: dict[str, str] = {}
for pair in _raw_keys.split(","):
    if ":" in pair:
        k, role = pair.strip().split(":", 1)
        API_KEYS[k.strip()] = role.strip()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
apikey_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

DEMO_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),
        "roles": ["admin"],
        "allowed_tenants": ["*"],
    },
    "readonly": {
        "username": "readonly",
        "hashed_password": pwd_context.hash("readonly"),
        "roles": ["reader"],
        "allowed_tenants": ["*"],
    },
    "bank001user": {
        "username": "bank001user",
        "hashed_password": pwd_context.hash("bank001pass"),
        "roles": ["reader"],
        "allowed_tenants": ["BANK001"],  # Yalnızca BANK001 verisine erişebilir
    },
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = DEMO_USERS.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(apikey_scheme),
) -> dict:
    """
    JWT Bearer VEYA X-API-Key header ile kimlik doğrular.
    İkisi de yoksa veya geçersizse 401 fırlatır.
    """

    if api_key:
        role = API_KEYS.get(api_key)
        if role:
            return {"username": f"api_key:{role}", "roles": [role], "auth_method": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("sub")
            if not username:
                raise ValueError
        except (JWTError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = DEMO_USERS.get(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı"
            )
        return {**user, "auth_method": "jwt"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulama gerekli: Bearer token veya X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )
