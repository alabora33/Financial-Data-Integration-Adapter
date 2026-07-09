"""
JWT tabanlı + API Key kimlik doğrulama.

Üç yol desteklenir:
  1. Bearer JWT  → POST /auth/token'dan alınan token
  2. API Key     → X-API-Key header (ortam değişkeni ile yönetilir)
  3. Kullanıcı kaydı → POST /auth/register
"""

import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-insecure-secret-change-in-production")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))

# Format: key:role  VEYA  key:role:TENANT1|TENANT2
# Örnek: teamsec-dev-key:admin,bank001-key:reader:BANK001
_raw_keys = os.environ.get("API_KEYS", "teamsec-dev-key:admin")
API_KEYS: dict[str, dict] = {}
for pair in _raw_keys.split(","):
    parts = pair.strip().split(":")
    if len(parts) >= 2:
        k = parts[0].strip()
        role = parts[1].strip()
        tenants_raw = parts[2].strip() if len(parts) >= 3 else "*"
        tenants = [t.strip() for t in tenants_raw.split("|")]
        API_KEYS[k] = {"role": role, "allowed_tenants": tenants}

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

# Kayıtlı kullanıcıları kalcı dosyada sakla (api/ klasörü Docker volume ile bağlı)
USERS_FILE = Path(__file__).parent / "users.json"
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
_users_lock = threading.Lock()


def _load_registered_users() -> dict:
    """Kayıtlı kullanıcıları dosyadan yükler. Dosya yoksa boş dict döner."""
    if not USERS_FILE.exists():
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_registered_user(username: str, user: dict) -> None:
    """Yeni kullanıcıyı dosyaya atomik olarak ekler."""
    with _users_lock:
        users = _load_registered_users()
        users[username] = user
        tmp = USERS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        tmp.replace(USERS_FILE)


def register_user(username: str, password: str) -> dict:
    """
    Yeni kullanıcı kaydeder.
    - Kullanıcı adı: 3-32 karakter, [a-zA-Z0-9_]
    - Şifre: en az 6 karakter
    - Varsayılan rol: reader, tüm tenant'lara erişim
    ValueError: kullanıcı adı alındıysa
    """
    if not _USERNAME_RE.match(username):
        raise ValueError("Kullanıcı adı 3-32 karakter olmalı, sadece harf/rakam/alt çizgi.")
    if len(password) < 6:
        raise ValueError("Şifre en az 6 karakter olmalıdır.")
    if username in DEMO_USERS:
        raise ValueError("Bu kullanıcı adı kullanımda.")

    hashed = pwd_context.hash(password)
    user = {
        "username": username,
        "hashed_password": hashed,
        "roles": ["reader"],
        "allowed_tenants": ["*"],
    }
    with _users_lock:
        if username in _load_registered_users():
            raise ValueError("Bu kullanıcı adı kullanımda.")
        tmp = USERS_FILE.with_suffix(".tmp")
        existing = _load_registered_users()
        existing[username] = user
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        tmp.replace(USERS_FILE)
    return user

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Demo kullanıcıları ve kayıtlı kullanıcılar arasında arar."""
    user = DEMO_USERS.get(username) or _load_registered_users().get(username)
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
        entry = API_KEYS.get(api_key)
        if entry:
            return {
                "username": f"api_key:{entry['role']}",
                "roles": [entry['role']],
                "auth_method": "api_key",
                "allowed_tenants": entry["allowed_tenants"],
            }
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
        user = DEMO_USERS.get(username) or _load_registered_users().get(username)
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
