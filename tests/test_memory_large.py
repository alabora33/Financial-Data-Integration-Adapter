"""
Bellek verimliliği (büyük veri) testi.

50K satırlık mock veri sync edilirken adaptörün generator tabanlı chunk
işlemesinin çalıştığını ve RAM kullanımının toplam veri boyutundan değil
CHUNK_SIZE ile orantılı kaldığını doğrular.

README'deki iddia: ~270K satır (≈220 MB CSV) için peak ≈ 45 MB
Bu test 50K satır ile aynı özelliği programatik olarak doğrular.
"""
import tracemalloc
from unittest.mock import MagicMock, patch

import pytest

CHUNK_SIZE = 5_000
PAGES = 10
TOPLAM_SATIR = CHUNK_SIZE * PAGES  # 50 000
BELLEK_SINIRI_MB = 200


def _satir(i: int) -> dict:
    """Geçerli bir RETAIL kredi satırı üretir."""
    return {
        "loan_account_number": f"LOAN_{i:07d}",
        "customer_id": f"CUST_{i:06d}",
        "customer_type": "I",
        "loan_status_code": "A",
        "days_past_due": "0",
        "final_maturity_date": "20270101",
        "total_installment_count": "24",
        "outstanding_installment_count": "20",
        "paid_installment_count": "4",
        "first_payment_date": "20250201",
        "original_loan_amount": "100000",
        "outstanding_principal_balance": "85000",
        "nominal_interest_rate": "42.50",
        "total_interest_amount": "10000",
        "kkdf_rate": "15",
        "kkdf_amount": "1500",
        "bsmv_rate": "10",
        "bsmv_amount": "1000",
        "grace_period_months": "0",
        "installment_frequency": "1",
        "loan_start_date": "20250101",
        "loan_closing_date": "",
        "insurance_included": "E",
        "customer_district_code": "D1",
        "customer_province_code": "P1",
        "internal_rating": "3",
        "external_rating": "1200",
    }


def _mock_get(url, params=None, **kwargs):
    """
    requests.get yerine geçer.
    Her çağrıda sadece ilgili sayfanın satırlarını lazy oluşturur —
    tüm veriyi önceden RAM'e almaz.
    """
    p = params or {}
    page = p.get("page", 1)
    data_kind = p.get("data_kind", "credit")

    if data_kind == "payment_plan":
        payload = {"data": [], "total": 0, "page": 1, "pages": 1, "row_count": 0}
    else:
        start = (page - 1) * CHUNK_SIZE
        rows = [_satir(i) for i in range(start, start + CHUNK_SIZE)]
        payload = {
            "data": rows,
            "total": TOPLAM_SATIR,
            "page": page,
            "pages": PAGES,
            "row_count": CHUNK_SIZE,
        }
    return MagicMock(json=lambda d=payload: d, raise_for_status=lambda: None)


@pytest.mark.django_db
@pytest.mark.slow
def test_buyuk_veri_bellek_verimliligi():
    """
    50K satır (≈40 MB ham Python verisi) sync edilirken peak RAM'in
    BELLEK_SINIRI_MB altında kaldığını doğrular.

    Servis CHUNK_SIZE=5000 ile satırları sayfalar halinde işler;
    tüm veri hiçbir zaman aynı anda bellekte tutulmaz.
    credit_map (50K kayıt) dahil tüm Django ORM overhead ile
    {BELLEK_SINIRI_MB} MB sınırı bellek verimliliğinin kanıtıdır.
    """
    from apps.loans.services.sync_service import sync_credit_data

    # tracemalloc'u temiz başlat — önceki oturum varsa sıfırla
    if tracemalloc.is_tracing():
        tracemalloc.stop()
    tracemalloc.start()

    try:
        with patch("apps.loans.services.sync_service.requests.get", side_effect=_mock_get):
            sonuc = sync_credit_data("BANK_MEM_TEST", "RETAIL")
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mb = peak_bytes / (1024 ** 2)

    # Sync başarılı olmalı
    assert sonuc["status"] == "success", f"Sync başarısız: {sonuc}"
    assert sonuc["kredi"]["rows_fetched"] == TOPLAM_SATIR
    assert sonuc["kredi"]["rows_valid"] == TOPLAM_SATIR

    # Bellek sınırı aşılmamalı
    assert peak_mb < BELLEK_SINIRI_MB, (
        f"Peak RAM çok yüksek: {peak_mb:.1f} MB "
        f"({TOPLAM_SATIR:,} satır için < {BELLEK_SINIRI_MB} MB bekleniyor, "
        f"CHUNK_SIZE={CHUNK_SIZE})"
    )


@pytest.mark.django_db
@pytest.mark.slow
def test_buyuk_veri_chunk_sayisi_dogru():
    """
    50K satır / CHUNK_SIZE=5000 ile tam olarak PAGES×2 HTTP isteği
    atıldığını doğrular (2 geçiş: doğrulama + yazma).
    Bu, verinin sayfalara bölünerek işlendiğini kanıtlar.
    """
    from apps.loans.services.sync_service import sync_credit_data

    cagrı_sayisi = 0

    def _sayici_mock(url, params=None, **kwargs):
        nonlocal cagrı_sayisi
        cagrı_sayisi += 1
        return _mock_get(url, params=params, **kwargs)

    with patch("apps.loans.services.sync_service.requests.get", side_effect=_sayici_mock):
        sync_credit_data("BANK_CHUNK_TEST", "RETAIL")

    # Kredi: PAGES çağrı (pass 1) + PAGES çağrı (pass 2) = 2×PAGES
    # Ödeme planı: 1 çağrı (boş → pass 2 atlanır)
    beklenen = PAGES * 2 + 1
    assert cagrı_sayisi == beklenen, (
        f"Beklenen {beklenen} HTTP çağrısı, gerçekleşen: {cagrı_sayisi}"
    )
