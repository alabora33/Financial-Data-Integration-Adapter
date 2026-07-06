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
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)