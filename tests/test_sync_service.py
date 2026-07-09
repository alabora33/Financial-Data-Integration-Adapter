"""
Sync service testleri.
HTTP çağrıları mock'lanır — external_bank çalışmak zorunda değil.
Cross-file validation mantığı burada test edilir.
"""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.loans.models import Tenant, CreditRecord, PaymentPlan, SyncLog


def _bank_yaniti(rows, total=None, page=1, pages=1):
    """Sahte external_bank /data yanıtı oluşturur."""
    total = total or len(rows)
    return MagicMock(
        json=lambda: {
            "data": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "row_count": len(rows),
        },
        raise_for_status=lambda: None,
    )


KREDI_SATIRLARI = [
    {
        "loan_account_number": "LOAN_000001",
        "customer_id": "CUST_001",
        "customer_type": "I",
        "loan_status_code": "A",
        "days_past_due": "0",
        "final_maturity_date": "20260302",
        "total_installment_count": "12",
        "outstanding_installment_count": "9",
        "paid_installment_count": "3",
        "first_payment_date": "20250402",
        "original_loan_amount": "50000",
        "outstanding_principal_balance": "38000",
        "nominal_interest_rate": "45.00",
        "total_interest_amount": "900",
        "kkdf_rate": "15",
        "kkdf_amount": "135",
        "bsmv_rate": "10",
        "bsmv_amount": "90",
        "grace_period_months": "0",
        "installment_frequency": "1",
        "loan_start_date": "20250302",
        "loan_closing_date": "",
        "insurance_included": "E",
        "customer_district_code": "D1",
        "customer_province_code": "P1",
        "internal_rating": "3",
        "external_rating": "1200",
    }
]

PLAN_SATIRLARI = [
    {
        "loan_account_number": "LOAN_000001",
        "installment_number": "1",
        "actual_payment_date": "20250402",
        "scheduled_payment_date": "20250402",
        "installment_amount": "4583.33",
        "principal_component": "4166.67",
        "interest_component": "375.00",
        "kkdf_component": "22.50",
        "bsmv_component": "18.75",
        "installment_status": "K",
        "remaining_principal": "45833.33",
        "remaining_interest": "4125.00",
        "remaining_kkdf": "247.50",
        "remaining_bsmv": "206.25",
    }
]


@pytest.mark.django_db
class TestSyncCreditData:

    @patch("apps.loans.services.sync_service.requests.get")
    def test_basarili_sync(self, mock_get):
        mock_get.side_effect = [
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 1 (doğrulama)
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 2 (yazma)
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 1 (doğrulama)
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 2 (yazma)
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sonuc = sync_credit_data("BANK001", "RETAIL")

        assert sonuc["status"] == "success"
        assert sonuc["kredi"]["rows_valid"] == 1
        assert sonuc["odeme_plani"]["rows_valid"] == 1

        assert CreditRecord.objects.filter(loan_account_number="LOAN_000001").count() == 1
        assert PaymentPlan.objects.filter(installment_number=1).count() == 1

    @patch("apps.loans.services.sync_service.requests.get")
    def test_hatali_kredi_sayilir(self, mock_get):
        hatali_satir = {**KREDI_SATIRLARI[0], "loan_account_number": ""}
        mock_get.side_effect = [
            _bank_yaniti([hatali_satir]),
            _bank_yaniti([]),
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sonuc = sync_credit_data("BANK001", "RETAIL")

        assert sonuc["kredi"]["rows_invalid"] == 1
        assert sonuc["kredi"]["rows_valid"] == 0

    @patch("apps.loans.services.sync_service.requests.get")
    def test_cross_file_validation_hatasi(self, mock_get):
        """
        Ödeme planındaki loan_account_number kredi kayıtlarında yoksa
        rows_invalid_cross artar.
        """
        yabanci_plan = {**PLAN_SATIRLARI[0], "loan_account_number": "LOAN_YABANCI"}
        mock_get.side_effect = [
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 1 (doğrulama)
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 2 (yazma)
            _bank_yaniti([yabanci_plan]),     # plan geçiş 1 (tümü cross-geçersiz, erken dönüş)
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sonuc = sync_credit_data("BANK001", "RETAIL")

        assert sonuc["odeme_plani"]["rows_invalid_cross"] == 1
        assert sonuc["odeme_plani"]["rows_valid"] == 0
        assert PaymentPlan.objects.count() == 0

    @patch("apps.loans.services.sync_service.requests.get")
    def test_atomik_replacement_eski_veri_silinir(self, mock_get):
        """Sync iki kez çalışınca eski veri silinip yenisi yazılır."""
        mock_get.side_effect = [
            _bank_yaniti(KREDI_SATIRLARI),   # 1. sync: kredi geçiş 1
            _bank_yaniti(KREDI_SATIRLARI),   # 1. sync: kredi geçiş 2
            _bank_yaniti(PLAN_SATIRLARI),    # 1. sync: plan geçiş 1
            _bank_yaniti(PLAN_SATIRLARI),    # 1. sync: plan geçiş 2
            _bank_yaniti(KREDI_SATIRLARI),   # 2. sync: kredi geçiş 1
            _bank_yaniti(KREDI_SATIRLARI),   # 2. sync: kredi geçiş 2
            _bank_yaniti(PLAN_SATIRLARI),    # 2. sync: plan geçiş 1
            _bank_yaniti(PLAN_SATIRLARI),    # 2. sync: plan geçiş 2
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK001", "RETAIL")
        sync_credit_data("BANK001", "RETAIL")

        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 1
        assert PaymentPlan.objects.count() == 1

    @patch("apps.loans.services.sync_service.requests.get")
    def test_bank_hatasi_sync_log_failed(self, mock_get):
        """Banka erişilemezse SyncLog FAILED olarak kaydedilir."""
        import requests as req_lib

        mock_get.side_effect = req_lib.exceptions.ConnectionError("bağlantı kurulamadı")

        from apps.loans.services.sync_service import sync_credit_data

        with pytest.raises(req_lib.exceptions.ConnectionError):
            sync_credit_data("BANK001", "RETAIL")

        log = SyncLog.objects.latest("sync_started_at")
        assert log.status == "FAILED"
        assert "bağlantı" in log.error_message

    @patch("apps.loans.services.sync_service.requests.get")
    def test_sync_log_tenant_olusturur(self, mock_get):
        """Tenant yoksa otomatik oluşturulur."""
        mock_get.side_effect = [
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 1
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 2
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 1
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 2
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK999", "RETAIL")

        assert Tenant.objects.filter(bank_code="BANK999").exists()

    # ── TC-04 ────────────────────────────────────────────────────────────
    @patch("apps.loans.services.sync_service.requests.get")
    def test_tum_satirlar_gecersiz_eski_veri_korunur(self, mock_get):
        """
        TC-04: Tüm satırlar geçersizse eski geçerli veri korunmalı.
        Kritik iş kuralı — sync_service.py satır 79-86.
        """
        hatali_satir = {**KREDI_SATIRLARI[0], "loan_account_number": ""}
        mock_get.side_effect = [
            # 1. sync: geçerli veri (iki geçiş)
            _bank_yaniti(KREDI_SATIRLARI),
            _bank_yaniti(KREDI_SATIRLARI),
            _bank_yaniti(PLAN_SATIRLARI),
            _bank_yaniti(PLAN_SATIRLARI),
            # 2. sync: tüm satırlar hatali (kredi: geçiş 1 erken dönüş; plan: rows_fetched=0 erken dönüş)
            _bank_yaniti([hatali_satir]),
            _bank_yaniti([]),
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK001", "RETAIL")
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 1

        sonuc = sync_credit_data("BANK001", "RETAIL")

        # Eski veri korundu
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 1
        assert sonuc["kredi"]["rows_valid"] == 0
        assert sonuc["kredi"]["rows_deleted_before_sync"] == 0
        assert "warning" in sonuc["kredi"]

    # ── TC-01 ────────────────────────────────────────────────────────────
    @patch("apps.loans.services.sync_service.requests.get")
    def test_tenant_izolasyonu(self, mock_get):
        """
        TC-01: BANK001 sync edilince BANK002 verisi etkilenmemeli.
        """
        mock_get.side_effect = [
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 1
            _bank_yaniti(KREDI_SATIRLARI),   # kredi geçiş 2
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 1
            _bank_yaniti(PLAN_SATIRLARI),    # plan geçiş 2
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK001", "RETAIL")

        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 1
        assert CreditRecord.objects.filter(tenant__bank_code="BANK002").count() == 0

    # ── TC-03 ────────────────────────────────────────────────────────────
    @patch("apps.loans.services.sync_service.requests.get")
    def test_replacement_1000_2000(self, mock_get):
        """
        TC-03: 2. sync append etmez; eski veri silinip yenisi yazılır.
        3 kayıt → 5 kayıt sync yapılınca toplam 5 olmalı (8 değil).
        """
        satirlar_3 = [
            {**KREDI_SATIRLARI[0], "loan_account_number": f"LOAN_{i:06d}"}
            for i in range(3)
        ]
        satirlar_5 = [
            {**KREDI_SATIRLARI[0], "loan_account_number": f"LOAN_{i:06d}"}
            for i in range(5)
        ]
        mock_get.side_effect = [
            _bank_yaniti(satirlar_3),   # 1. sync: kredi geçiş 1
            _bank_yaniti(satirlar_3),   # 1. sync: kredi geçiş 2
            _bank_yaniti([]),           # 1. sync: plan (0 satır, erken dönüş)
            _bank_yaniti(satirlar_5),   # 2. sync: kredi geçiş 1
            _bank_yaniti(satirlar_5),   # 2. sync: kredi geçiş 2
            _bank_yaniti([]),           # 2. sync: plan (0 satır, erken dönüş)
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK001", "RETAIL")
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 3

        sonuc = sync_credit_data("BANK001", "RETAIL")
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 5
        assert sonuc["kredi"]["rows_deleted_before_sync"] == 3
        assert sonuc["kredi"]["rows_valid"] == 5

    # ── TC-02 ────────────────────────────────────────────────────────────
    @patch("apps.loans.services.sync_service.requests.get")
    def test_retail_commercial_ayri_sync(self, mock_get):
        """
        TC-02: Aynı tenant için RETAIL ve COMMERCIAL bağımsız olarak
        sync edilebilmeli; kayıtlar birbirine karışmamalı.
        """
        retail_satir = {**KREDI_SATIRLARI[0], "loan_account_number": "LOAN_RETAIL_001"}
        commercial_satir = {
            **KREDI_SATIRLARI[0],
            "loan_account_number": "LOAN_COM_001",
            "customer_type": "C",
        }
        mock_get.side_effect = [
            _bank_yaniti([retail_satir]),     # RETAIL: kredi geçiş 1
            _bank_yaniti([retail_satir]),     # RETAIL: kredi geçiş 2
            _bank_yaniti([]),                 # RETAIL: plan (0 satır, erken dönüş)
            _bank_yaniti([commercial_satir]), # COMMERCIAL: kredi geçiş 1
            _bank_yaniti([commercial_satir]), # COMMERCIAL: kredi geçiş 2
            _bank_yaniti([]),                 # COMMERCIAL: plan (0 satır, erken dönüş)
        ]
        from apps.loans.services.sync_service import sync_credit_data

        sync_credit_data("BANK001", "RETAIL")
        sync_credit_data("BANK001", "COMMERCIAL")

        assert CreditRecord.objects.filter(tenant__bank_code="BANK001", loan_type="RETAIL").count() == 1
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001", loan_type="COMMERCIAL").count() == 1
        assert CreditRecord.objects.filter(tenant__bank_code="BANK001").count() == 2
