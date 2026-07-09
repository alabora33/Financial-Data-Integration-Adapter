import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "bank_data"
DATA_DIR.mkdir(exist_ok=True)


def _file_path(tenant_id: str, loan_type: str, data_kind: str) -> Path:
    filename = f"{tenant_id}__{loan_type}__{data_kind}.jsonl"
    return DATA_DIR / filename


def save_data(tenant_id: str, loan_type: str, data_kind: str, rows: list) -> None:
    """Her satırı ayrı JSON objesi olarak JSONL formatında yazar."""
    path = _file_path(tenant_id, loan_type, data_kind)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_data_streaming(tenant_id: str, loan_type: str, data_kind: str, reader) -> int:
    """
    CSV DictReader'dan satırları belleğe yüklemeden doğrudan JSONL olarak diske yazar.
    Bellek kullanımı: O(1) — her satır işlendikten sonra atılır.
    Döndürür: yazılan satır sayısı.
    """
    path = _file_path(tenant_id, loan_type, data_kind)
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in reader:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_data(tenant_id: str, loan_type: str, data_kind: str) -> list:
    """Tüm veriyi döndürür (geriye dönük uyumluluk)."""
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_data_page(
    tenant_id: str,
    loan_type: str,
    data_kind: str,
    page: int = 1,
    page_size: int = 5000,
) -> tuple[list, int]:
    """
    JSONL dosyasını satır satır okuyarak sayfalı veri döndürür.
    Hiçbir noktada tüm dosya belleğe alınmaz — gerçek streaming.
    """
    path = _file_path(tenant_id, loan_type, data_kind)
    if not path.exists():
        return [], 0

    start = (page - 1) * page_size
    end = start + page_size

    rows: list = []
    total = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if start <= total < end:
                rows.append(json.loads(line))
            total += 1

    return rows, total
