import os
import httpx
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

ADAPTER_URL = os.environ.get("ADAPTER_BASE_URL", "http://adapter:8002")

app = FastAPI(
    title="TeamSec Adapter API",
    description="Finansal Veri Entegrasyon Adaptörü — Genel API Katmanı",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "adapter-api", "version": "1.0.0"}


@app.post("/api/sync")
async def trigger_sync(tenant_id: str, loan_type: str = "RETAIL"):
    """
    Bankadan veri senkronizasyonunu başlatır.
    adapter/ Django servisini çağırır, o da external_bank'tan çeker.
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{ADAPTER_URL}/internal/sync/",
                json={"bank_code": tenant_id, "loan_type": loan_type},
                timeout=120.0,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Adapter servisine ulaşılamıyor: {e}")


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
