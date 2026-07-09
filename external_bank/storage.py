import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).parent / "bank_data"
DATA_DIR.mkdir(exist_ok=True)

_CACHE: dict[str, dict] = {}
CACHE_TTL = 600


def _cache_get(path: Path) -> list | None:
    key = str(path)
    entry = _CACHE.get(key)
    if not entry:
        return None

    try:
        current_mtime = path.stat().st_mtime
    except FileNotFoundError:
        return None
    if entry["mtime"] != current_mtime:
        del _CACHE[key]
        return None

    if time.time() - entry["loaded_at"] > CACHE_TTL:
        del _CACHE[key]
        return None
    return entry["rows"]


def _cache_set(path: Path, rows: list) -> None:
    _CACHE[str(path)] = {
        "rows": rows,
        "loaded_at": time.time(),
        "mtime": path.stat().st_mtime,
    }


def _file_path(tenant_id: str, loan_type: str, data_kind: str) -> Path:
    filename = f"{tenant_id}__{loan_type}__{data_kind}.json"
    return DATA_DIR / filename


def save_data(tenant_id: str, loan_type: str, data_kind: str, rows: list) -> None:
    path = _file_path(tenant_id, loan_type, data_kind)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    _CACHE.pop(str(path), None)


def load_data(tenant_id: str, loan_type: str, data_kind: str) -> list:
    """Tüm veriyi döndürür (geriye dönük uyumluluk)."""
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return []
    rows = _cache_get(path)
    if rows is None:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        _cache_set(path, rows)
    return rows


def load_data_page(
    tenant_id: str,
    loan_type: str,
    data_kind: str,
    page: int = 1,
    page_size: int = 5000,
) -> tuple[list, int]:
    """
    Veriyi sayfa sayfa döndürür.
    JSON dosyası ilk istekte bir kez yüklenir, sonraki sayfa isteklerinde
    cache'den hızla okunur — büyük dosyalar için kritik.
    """
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return [], 0

    all_rows = _cache_get(path)
    if all_rows is None:
        with open(path, "r", encoding="utf-8") as f:
            all_rows = json.load(f)
        _cache_set(path, all_rows)

    total = len(all_rows)
    start = (page - 1) * page_size
    end = start + page_size
    return all_rows[start:end], total
