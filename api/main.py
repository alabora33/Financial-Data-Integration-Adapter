import os
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="TeamSec Adapter API",
    description="Finansal Veri Entegrasyon Adaptörü — Genel API Katmanı",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "adapter-api", "version": "1.0.0"}


@app.post("/api/sync")
def trigger_sync(tenant_id: str, loan_type: str):
    """
    Belirtilen kiracı ve kredi tipi için banka verisi senkronizasyonunu başlatır.
    Faz 3'te implement edilecek.
    """
    return {
        "status": "not_implemented",
        "message": "Sync motoru Faz 3'te eklenecek",
        "tenant_id": tenant_id,
        "loan_type": loan_type,
    }


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
