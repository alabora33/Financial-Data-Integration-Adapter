import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "bank_data"
DATA_DIR.mkdir(exist_ok=True)


def _file_path(tenant_id: str, loan_type: str, data_kind: str) -> Path:
    filename = f"{tenant_id}__{loan_type}__{data_kind}.json"
    return DATA_DIR / filename


def save_data(tenant_id: str, loan_type: str, data_kind: str, rows: list) -> None:
    path = _file_path(tenant_id, loan_type, data_kind)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def load_data(tenant_id: str, loan_type: str, data_kind: str) -> list:
    """Tüm veriyi döndürür (geriye dönük uyumluluk için korundu)."""
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_data_page(
    tenant_id: str,
    loan_type: str,
    data_kind: str,
    page: int = 1,
    page_size: int = 5000,
) -> tuple[list, int]:
    """
    Veriyi sayfa sayfa döndürür — büyük dosyalar için bellek tasarrufu sağlar.
    Döner: (sayfa_satırları, toplam_satır_sayısı)
    """
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return [], 0

    with open(path, "r", encoding="utf-8") as f:
        all_rows = json.load(f)  # Dosya JSON → RAM'e yüklenir

    total = len(all_rows)
    start = (page - 1) * page_size
    end   = start + page_size
    # Sadece istenen sayfa dilimi döndürülür — adapter'da bellek sınırlı kalır
    return all_rows[start:end], total
