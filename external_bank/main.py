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
    contents = await file.read()
    text = contents.decode("utf-8")

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV boş veya okunamadı")

    storage.save_data(tenant_id, loan_type, data_kind, rows)

    return {
        "message": "yükleme başarılı",
        "tenant_id": tenant_id,
        "loan_type": loan_type,
        "data_kind": data_kind,
        "row_count": len(rows),
    }


@app.get("/data")
def get_data(tenant_id: str, loan_type: str, data_kind: str):
    rows = storage.load_data(tenant_id, loan_type, data_kind)
    return {
        "tenant_id": tenant_id,
        "loan_type": loan_type,
        "data_kind": data_kind,
        "row_count": len(rows),
        "data": rows,
    }