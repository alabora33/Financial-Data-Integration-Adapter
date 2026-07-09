import os
import requests
from django.db import transaction
from django.utils import timezone

from ..models import Tenant, CreditRecord, SyncLog
from .validator import validate_retail_credit, validate_commercial_credit
from .normalizer import normalize_retail_credit, normalize_commercial_credit

BANK_BASE_URL = os.environ.get("BANK_BASE_URL", "http://external_bank:8001")

VALIDATORS = {
    "RETAIL":     validate_retail_credit,
    "COMMERCIAL": validate_commercial_credit,
}

NORMALIZERS = {
    "RETAIL":     normalize_retail_credit,
    "COMMERCIAL": normalize_commercial_credit,
}


def sync_credit_data(bank_code: str, loan_type: str) -> dict:
    """
    1. external_bank'tan kredi verisini çek
    2. Her satırı doğrula ve normalize et
    3. Atomik transaction ile eski veriyi sil, yeniyi yaz
    4. SyncLog'u güncelle, istatistikleri dön
    """
    validate = VALIDATORS[loan_type]
    normalize = NORMALIZERS[loan_type]

    # Tenant bul veya oluştur (get_or_create: tek sorguda bul ya da yarat)
    tenant, _ = Tenant.objects.get_or_create(bank_code=bank_code)

    # Sync kaydını PENDING olarak aç
    sync_log = SyncLog.objects.create(
        tenant=tenant,
        loan_type=loan_type,
        status="PENDING",
    )

    try:
        # --- 1. Bankadan çek ---
        resp = requests.get(
            f"{BANK_BASE_URL}/data",
            params={"tenant_id": bank_code, "loan_type": loan_type, "data_kind": "credit"},
            timeout=60,
        )
        resp.raise_for_status()
        rows = resp.json().get("data", [])

        # --- 2. Doğrula + normalize ---
        rows_fetched = len(rows)
        gecerli_satirlar = []
        hatali_sayisi = 0

        for row in rows:
            sonuc = validate(row)
            if sonuc.gecerli:
                gecerli_satirlar.append(normalize(row))
            else:
                hatali_sayisi += 1

        # --- 3. Atomik kayıt (eski veriyi sil → yeniyi yaz) ---
        with transaction.atomic():
            silinen, _ = CreditRecord.objects.filter(
                tenant=tenant, loan_type=loan_type
            ).delete()

            CreditRecord.objects.bulk_create(
                [CreditRecord(tenant=tenant, loan_type=loan_type, **veri)
                 for veri in gecerli_satirlar],
                batch_size=500,
            )

        # --- 4. Log güncelle ---
        sync_log.status = "SUCCESS"
        sync_log.rows_fetched = rows_fetched
        sync_log.rows_valid = len(gecerli_satirlar)
        sync_log.rows_invalid = hatali_sayisi
        sync_log.sync_finished_at = timezone.now()
        sync_log.save()

        return {
            "status": "success",
            "bank_code": bank_code,
            "loan_type": loan_type,
            "rows_fetched": rows_fetched,
            "rows_valid": len(gecerli_satirlar),
            "rows_invalid": hatali_sayisi,
            "rows_deleted_before_sync": silinen,
        }

    except Exception as e:
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.sync_finished_at = timezone.now()
        sync_log.save()
        raise
