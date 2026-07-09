import csv
import io

from fastapi import FastAPI, UploadFile, File, HTTPException

import storage

app = FastAPI(title="Simüle Banka Servisi")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "external_bank"}


@app.post("/upload")
async def upload_csv(
    tenant_id: str,
    loan_type: str,
    data_kind: str,
    file: UploadFile = File(...),
):
    # SpooledTemporaryFile üzerinden doğrudan aktarım — tüm satırlar belleğe yüklenmez
    text_stream = io.TextIOWrapper(file.file, encoding="utf-8")
    reader = csv.DictReader(text_stream, delimiter=";")
    row_count = storage.save_data_streaming(tenant_id, loan_type, data_kind, reader)

    if row_count == 0:
        raise HTTPException(status_code=400, detail="CSV boş veya okunamadı")

    return {
        "message": "yükleme başarılı",
        "tenant_id": tenant_id,
        "loan_type": loan_type,
        "data_kind": data_kind,
        "row_count": row_count,
    }


@app.get("/data")
def get_data(
    tenant_id: str,
    loan_type: str,
    data_kind: str,
    page: int = 1,
    page_size: int = 5000,
):
    """
    Kayıtlı veriyi sayfalı döndürür.
    page_size varsayılanı 5000 — adapter büyük veri setlerini chunk'lar halinde çeker.
    """
    rows, total = storage.load_data_page(tenant_id, loan_type, data_kind, page, page_size)
    pages = max(1, (total + page_size - 1) // page_size)
    return {
        "tenant_id": tenant_id,
        "loan_type": loan_type,
        "data_kind": data_kind,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "row_count": len(rows),
        "data": rows,
    }
