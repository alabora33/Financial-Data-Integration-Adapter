import os
import requests
from django.db import transaction
from django.utils import timezone

from ..models import Tenant, CreditRecord, PaymentPlan, SyncLog
from .validator import validate_retail_credit, validate_commercial_credit, validate_payment_plan
from .normalizer import normalize_retail_credit, normalize_commercial_credit, normalize_payment_plan

BANK_BASE_URL = os.environ.get("BANK_BASE_URL", "http://external_bank:8001")

CHUNK_SIZE = int(os.environ.get("SYNC_CHUNK_SIZE", "5000"))

CREDIT_VALIDATORS = {
    "RETAIL": validate_retail_credit,
    "COMMERCIAL": validate_commercial_credit,
}
CREDIT_NORMALIZERS = {
    "RETAIL": normalize_retail_credit,
    "COMMERCIAL": normalize_commercial_credit,
}


def _fetch_all(bank_code: str, loan_type: str, data_kind: str):
    """
    Generator: external_bank'tan veriyi CHUNK_SIZE'lık sayfalarda çeker.
    Toplam veri büyüklüğünden bağımsız olarak bellekte sadece bir sayfa tutulur.
    Her iterasyonda (chunk_rows, total, pages) döner.
    """
    page = 1
    while True:
        resp = requests.get(
            f"{BANK_BASE_URL}/data",
            params={
                "tenant_id": bank_code,
                "loan_type": loan_type,
                "data_kind": data_kind,
                "page": page,
                "page_size": CHUNK_SIZE,
            },
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
        chunk = payload.get("data", [])
        total = payload.get("total", 0)
        pages = payload.get("pages", 1)

        if not chunk:
            break

        yield chunk, total, pages

        if page >= pages:
            break
        page += 1


def _sync_credits(tenant, bank_code: str, loan_type: str) -> dict:
    """
    Kredi kayıtlarını iki geçişte işler:
      Geçiş 1: Doğrula ve say — hepsi geçersizse eski veriyi koru, hiç silme.
      Geçiş 2: Eski veriyi sil, geçerli satırları chunk'lar halinde yaz.
    Bellek kullanımı: O(CHUNK_SIZE) — hiçbir zaman tek seferde tüm veri belleğe alınmaz.
    """
    validate = CREDIT_VALIDATORS[loan_type]
    normalize = CREDIT_NORMALIZERS[loan_type]

    # Geçiş 1: Doğrulama ve sayım
    rows_fetched = 0
    gecerli_sayisi = 0
    hatali = 0
    ornek_hatalar: list[str] = []

    for chunk, _, _ in _fetch_all(bank_code, loan_type, "credit"):
        rows_fetched += len(chunk)
        for row in chunk:
            sonuc = validate(row)
            if sonuc.gecerli:
                gecerli_sayisi += 1
            else:
                hatali += 1
                if len(ornek_hatalar) < 5:
                    loan_no = str(row.get("loan_account_number", "?"))[:20]
                    for e in sonuc.hatalar[:2]:
                        ornek_hatalar.append(f"{loan_no}: {e.alan} — {e.sebep}")

    if rows_fetched == 0 or gecerli_sayisi == 0:
        result: dict = {
            "rows_fetched": rows_fetched,
            "rows_valid": 0,
            "rows_invalid": hatali,
            "rows_deleted": 0,
            "ornek_hatalar": ornek_hatalar[:5],
        }
        if rows_fetched > 0:
            result["warning"] = "Tüm satırlar geçersiz — eski veri korundu"
        return result

    # Geçiş 2: Yazma — eski veriyi sil, geçerli satırları chunk'lar halinde yaz
    with transaction.atomic():
        silinen, _ = CreditRecord.objects.filter(tenant=tenant, loan_type=loan_type).delete()
        for chunk, _, _ in _fetch_all(bank_code, loan_type, "credit"):
            batch = [
                CreditRecord(tenant=tenant, loan_type=loan_type, **normalize(row))
                for row in chunk
                if validate(row).gecerli
            ]
            if batch:
                CreditRecord.objects.bulk_create(batch, batch_size=500)

    return {
        "rows_fetched": rows_fetched,
        "rows_valid": gecerli_sayisi,
        "rows_invalid": hatali,
        "rows_deleted": silinen,
        "ornek_hatalar": ornek_hatalar[:5],
    }


def _sync_payment_plans(tenant, bank_code: str, loan_type: str) -> dict:
    """
    Ödeme planlarını iki geçişte işler:
      Geçiş 1: Geçerli plan sayısını hesapla — hepsi geçersizse eski veriyi koru.
      Geçiş 2: Eski planları sil, geçerli satırları chunk'lar halinde yaz.
    Bellek kullanımı: CHUNK_SIZE × satır_boyutu (~3 MB/chunk)
    Cross-file validation: loan_account_number kredi kayıtlarında bulunmalı.
    """
    credit_map = {
        rec.loan_account_number: rec
        for rec in CreditRecord.objects.filter(tenant=tenant, loan_type=loan_type)
    }

    rows_fetched = 0
    rows_valid = 0
    alan_hatali = 0
    capraz_hatali = 0

    # Geçiş 1: Doğrulama ve sayım
    for chunk, _, _ in _fetch_all(bank_code, loan_type, "payment_plan"):
        rows_fetched += len(chunk)
        for row in chunk:
            if not validate_payment_plan(row).gecerli:
                alan_hatali += 1
                continue
            loan_acc = row.get("loan_account_number", "").strip()
            if loan_acc not in credit_map:
                capraz_hatali += 1
                continue
            rows_valid += 1

    if rows_fetched == 0 or rows_valid == 0:
        result: dict = {
            "rows_fetched": rows_fetched,
            "rows_valid": 0,
            "rows_invalid_field": alan_hatali,
            "rows_invalid_cross": capraz_hatali,
        }
        if rows_fetched > 0:
            result["warning"] = "Tüm ödeme planı satırları geçersiz — eski veri korundu"
        return result

    # Geçiş 2: Yazma — eski planları sil, geçerli satırları chunk'lar halinde yaz
    with transaction.atomic():
        PaymentPlan.objects.filter(
            credit__tenant=tenant,
            credit__loan_type=loan_type,
        ).delete()

        for chunk, _, _ in _fetch_all(bank_code, loan_type, "payment_plan"):
            gecerli_planlar = []

            for row in chunk:
                if not validate_payment_plan(row).gecerli:
                    continue
                loan_acc = row.get("loan_account_number", "").strip()
                credit = credit_map.get(loan_acc)
                if credit is None:
                    continue
                gecerli_planlar.append((credit, normalize_payment_plan(row)))

            if gecerli_planlar:
                PaymentPlan.objects.bulk_create(
                    [PaymentPlan(credit=credit, **veri) for credit, veri in gecerli_planlar],
                    batch_size=500,
                )

    return {
        "rows_fetched": rows_fetched,
        "rows_valid": rows_valid,
        "rows_invalid_field": alan_hatali,
        "rows_invalid_cross": capraz_hatali,
    }


def sync_credit_data(bank_code: str, loan_type: str) -> dict:
    """
    Uçtan uca senkronizasyon:
      1. Kredi kayıtlarını senkronize et
      2. Ödeme planlarını senkronize et (cross-file validation dahil)
      3. SyncLog güncelle, istatistikleri döndür
    """
    tenant, _ = Tenant.objects.get_or_create(bank_code=bank_code)

    sync_log = SyncLog.objects.create(
        tenant=tenant,
        loan_type=loan_type,
        status="PENDING",
    )

    try:
        kredi_sonuc = _sync_credits(tenant, bank_code, loan_type)
        plan_sonuc = _sync_payment_plans(tenant, bank_code, loan_type)

        sync_log.status = "SUCCESS"
        sync_log.rows_fetched = kredi_sonuc["rows_fetched"]
        sync_log.rows_valid = kredi_sonuc["rows_valid"]
        sync_log.rows_invalid = kredi_sonuc["rows_invalid"]
        sync_log.sync_finished_at = timezone.now()
        sync_log.save()

        kredi_blok = {
            "rows_fetched": kredi_sonuc["rows_fetched"],
            "rows_valid": kredi_sonuc["rows_valid"],
            "rows_invalid": kredi_sonuc["rows_invalid"],
            "rows_deleted_before_sync": kredi_sonuc["rows_deleted"],
        }
        if "warning" in kredi_sonuc:
            kredi_blok["warning"] = kredi_sonuc["warning"]
        if kredi_sonuc.get("ornek_hatalar"):
            kredi_blok["ornek_hatalar"] = kredi_sonuc["ornek_hatalar"]

        odeme_plani_blok = {
                "rows_fetched": plan_sonuc["rows_fetched"],
                "rows_valid": plan_sonuc["rows_valid"],
                "rows_invalid_field": plan_sonuc["rows_invalid_field"],
                "rows_invalid_cross": plan_sonuc["rows_invalid_cross"],
            }
        if "warning" in plan_sonuc:
            odeme_plani_blok["warning"] = plan_sonuc["warning"]

        return {
            "status": "success",
            "bank_code": bank_code,
            "loan_type": loan_type,
            "kredi": kredi_blok,
            "odeme_plani": odeme_plani_blok,
        }

    except Exception as e:
        sync_log.status = "FAILED"
        sync_log.error_message = str(e)
        sync_log.sync_finished_at = timezone.now()
        sync_log.save()
        raise
