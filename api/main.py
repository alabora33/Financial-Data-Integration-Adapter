import os
import httpx
from fastapi import FastAPI, HTTPException, Query, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv

from auth import authenticate_user, create_access_token, get_current_user

load_dotenv()

ADAPTER_URL = os.environ.get("ADAPTER_BASE_URL", "http://adapter:8002")
BANK_URL = os.environ.get("BANK_BASE_URL", "http://external_bank:8001")
INTERNAL_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "dev-internal-token-change-in-production")
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}

app = FastAPI(
    title="TeamSec Adapter API",
    description="Finansal Veri Entegrasyon Adaptörü — Genel API Katmanı",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _adapter_get(path: str, params: dict) -> dict:
    """adapter/ Django servisine GET isteği atar."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{ADAPTER_URL}{path}", params=params, headers=INTERNAL_HEADERS, timeout=60.0
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Adapter servisine ulaşılamıyor: {e}")


async def _adapter_post(path: str, body: dict) -> dict:
    """adapter/ Django servisine POST isteği atar."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{ADAPTER_URL}{path}", json=body, headers=INTERNAL_HEADERS, timeout=600.0
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Adapter servisine ulaşılamıyor: {e}")


class SyncRequest(BaseModel):
    tenant_id: str
    loan_type: str = "RETAIL"


def _check_tenant_access(user: dict, tenant_id: str) -> None:
    """Kullanıcının istenen tenant'a erişim izni olup olmadığını kontrol eder."""
    allowed = user.get("allowed_tenants", ["*"])
    if "*" not in allowed and tenant_id not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"{tenant_id} tenant'a erişim izniniz yok",
        )


@app.get("/health", tags=["Sistem"])
def health_check():
    return {"status": "ok", "service": "adapter-api", "version": "1.0.0"}


@app.post("/auth/token", tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    JWT token al. Demo: admin/admin · readonly/readonly
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user["username"])
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/sync", tags=["Senkronizasyon"])
async def trigger_sync(
    body: SyncRequest,
    _user: dict = Depends(get_current_user),
):
    """Senkronizasyon başlatir. JWT token gerektirir. Body: {tenant_id, loan_type}"""
    _check_tenant_access(_user, body.tenant_id)
    loan_type = body.loan_type.upper()
    if loan_type not in ("RETAIL", "COMMERCIAL"):
        raise HTTPException(status_code=400, detail="loan_type RETAIL veya COMMERCIAL olmalıdır")
    return await _adapter_post(
        "/internal/sync/",
        {"bank_code": body.tenant_id, "loan_type": loan_type},
    )


@app.get("/api/data", tags=["Veri"])
async def get_data(
    tenant_id: str = Query(..., description="Banka kodu"),
    loan_type: str = Query("RETAIL", description="RETAIL veya COMMERCIAL"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    _user: dict = Depends(get_current_user),
):
    """Normalize edilmiş kredi kayıtlarını sayfalı döndürür. JWT token gerektirir."""
    _check_tenant_access(_user, tenant_id)
    return await _adapter_get(
        "/internal/data/",
        {"tenant_id": tenant_id, "loan_type": loan_type, "page": page, "page_size": page_size},
    )


@app.get("/api/profiling", tags=["Veri Kalitesi"])
async def get_profiling(
    tenant_id: str = Query(..., description="Banka kodu"),
    loan_type: str = Query("RETAIL", description="RETAIL veya COMMERCIAL"),
    _user: dict = Depends(get_current_user),
):
    """Veri kalitesi profil raporu. JWT token gerektirir."""
    _check_tenant_access(_user, tenant_id)
    return await _adapter_get(
        "/internal/profiling/",
        {"tenant_id": tenant_id, "loan_type": loan_type},
    )


@app.post("/api/upload", tags=["Veri Yükleme"])
async def upload_csv(
    tenant_id: str = Query(..., description="Banka kodu (ör: BANK001)"),
    loan_type: str = Query(..., description="RETAIL veya COMMERCIAL"),
    data_kind: str = Query(..., description="credit veya payment_plan"),
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
):
    """
    CSV dosyasını banka simülatörüne yükler. JWT token gerektirir.
    data_kind: credit | payment_plan
    """
    _check_tenant_access(_user, tenant_id)
    loan_type = loan_type.upper()
    if loan_type not in ("RETAIL", "COMMERCIAL"):
        raise HTTPException(status_code=400, detail="loan_type RETAIL veya COMMERCIAL olmalıdır")
    if data_kind not in ("credit", "payment_plan"):
        raise HTTPException(status_code=400, detail="data_kind credit veya payment_plan olmalıdır")

    contents = await file.read()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{BANK_URL}/upload",
                params={"tenant_id": tenant_id, "loan_type": loan_type, "data_kind": data_kind},
                files={"file": (file.filename, contents, "text/csv")},
                timeout=120.0,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Banka servisine ulaşılamıyor: {e}")
