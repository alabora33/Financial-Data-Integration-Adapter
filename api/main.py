import os
import httpx
from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv

load_dotenv()

ADAPTER_URL = os.environ.get("ADAPTER_BASE_URL", "http://adapter:8002")

app = FastAPI(
    title="TeamSec Adapter API",
    description="Finansal Veri Entegrasyon Adaptörü — Genel API Katmanı",
    version="1.0.0",
)


# ─── Yardımcı ────────────────────────────────────────────────────────────────

async def _adapter_get(path: str, params: dict) -> dict:
    """adapter/ Django servisine GET isteği atar."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{ADAPTER_URL}{path}", params=params, timeout=60.0)
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
            resp = await client.post(f"{ADAPTER_URL}{path}", json=body, timeout=120.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Adapter servisine ulaşılamıyor: {e}")


# ─── Endpoint'ler ────────────────────────────────────────────────────────────

@app.get("/health", tags=["Sistem"])
def health_check():
    return {"status": "ok", "service": "adapter-api", "version": "1.0.0"}


@app.post("/api/sync", tags=["Senkronizasyon"])
async def trigger_sync(
    tenant_id: str = Query(..., description="Banka kodu (örn: BANK001)"),
    loan_type: str = Query("RETAIL", description="Kredi tipi: RETAIL veya COMMERCIAL"),
):
    """
    Belirtilen banka ve kredi tipi için senkronizasyon başlatır.
    external_bank'tan veri çeker, doğrular, normalize eder, PostgreSQL'e kaydeder.
    """
    return await _adapter_post(
        "/internal/sync/",
        {"bank_code": tenant_id, "loan_type": loan_type},
    )


@app.get("/api/data", tags=["Veri"])
async def get_data(
    tenant_id: str = Query(..., description="Banka kodu"),
    loan_type: str = Query("RETAIL", description="RETAIL veya COMMERCIAL"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    page_size: int = Query(100, ge=1, le=1000, description="Sayfa başına kayıt (maks 1000)"),
):
    """
    Normalize edilmiş kredi kayıtlarını sayfalı döndürür.
    """
    return await _adapter_get(
        "/internal/data/",
        {"tenant_id": tenant_id, "loan_type": loan_type, "page": page, "page_size": page_size},
    )


@app.get("/api/profiling", tags=["Veri Kalitesi"])
async def get_profiling(
    tenant_id: str = Query(..., description="Banka kodu"),
    loan_type: str = Query("RETAIL", description="RETAIL veya COMMERCIAL"),
):
    """
    Veri kalitesi profil raporu:
    faiz/tutar istatistikleri, boş alan oranları, kategorik dağılımlar, son sync bilgisi.
    """
    return await _adapter_get(
        "/internal/profiling/",
        {"tenant_id": tenant_id, "loan_type": loan_type},
    )



@app.get("/api/data")
def get_data(tenant_id: str, loan_type: str, page: int = 1, page_size: int = 100):
    """
    Normalize edilmiş kredi verilerini sayfalı olarak döndürür.
    Faz 3'te implement edilecek.
    """
    return {
        "status": "not_implemented",
        "message": "Data endpoint Faz 3'te eklenecek",
    }


@app.get("/api/profiling")
def get_profiling(tenant_id: str, loan_type: str):
    """
    Veri kalitesi profil raporunu döndürür.
    Faz 5'te implement edilecek.
    """
    return {
        "status": "not_implemented",
        "message": "Profiling endpoint Faz 5'te eklenecek",
    }
