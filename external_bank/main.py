from fastapi import FastAPI

app = FastAPI(title="Simüle Banka Servisi")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "external_bank"}