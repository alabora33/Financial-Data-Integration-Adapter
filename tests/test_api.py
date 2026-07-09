"""
Django DRF endpoint testleri.
/internal/sync/, /internal/data/, /internal/profiling/ test edilir.
"""
import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def dolu_db(tenant):
    """Birkaç CreditRecord ile dolu DB fixture'ı."""
    from apps.loans.models import CreditRecord
    records = []
    for i in range(5):
        records.append(CreditRecord.objects.create(
            tenant=tenant,
            loan_type="RETAIL",
            loan_account_number=f"LOAN_{i:06d}",
            customer_id=f"CUST_{i:05d}",
            customer_type="I",
            loan_status_code="A",
            loan_start_date=datetime.date(2025, 1, 1),
            final_maturity_date=datetime.date(2026, 1, 1),
            original_loan_amount=Decimal("50000"),
            outstanding_principal_balance=Decimal("40000"),
            nominal_interest_rate=Decimal("45.00"),
            total_interest_amount=Decimal("900"),
            insurance_included="E",
        ))
    return records


# ── Sync endpoint ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSyncEndpoint:

    def test_bank_code_eksik_400(self, client):
        resp = client.post(
            "/internal/sync/",
            data='{"loan_type": "RETAIL"}',
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "bank_code" in resp.json()["error"]

    def test_gecersiz_loan_type_400(self, client):
        resp = client.post(
            "/internal/sync/",
            data='{"bank_code": "BANK001", "loan_type": "INVALID"}',
            content_type="application/json",
        )
        assert resp.status_code == 400

    @patch("apps.loans.views.sync_credit_data")
    def test_basarili_sync_200(self, mock_sync, client):
        mock_sync.return_value = {"status": "success", "kredi": {}, "odeme_plani": {}}
        resp = client.post(
            "/internal/sync/",
            data='{"bank_code": "BANK001", "loan_type": "RETAIL"}',
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"
        mock_sync.assert_called_once_with("BANK001", "RETAIL")

    @patch("apps.loans.views.sync_credit_data")
    def test_sync_hatasi_500(self, mock_sync, client):
        mock_sync.side_effect = Exception("banka hatası")
        resp = client.post(
            "/internal/sync/",
            data='{"bank_code": "BANK001", "loan_type": "RETAIL"}',
            content_type="application/json",
        )
        assert resp.status_code == 500


# ── Data endpoint ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDataEndpoint:

    def test_tenant_id_eksik_400(self, client):
        resp = client.get("/internal/data/?loan_type=RETAIL")
        assert resp.status_code == 400

    def test_bos_sonuc(self, client, tenant):
        resp = client.get("/internal/data/?tenant_id=BANK001&loan_type=RETAIL")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_kayitlar_donuyor(self, client, dolu_db):
        resp = client.get("/internal/data/?tenant_id=BANK001&loan_type=RETAIL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["data"]) == 5

    def test_sayfalama(self, client, dolu_db):
        resp = client.get(
            "/internal/data/?tenant_id=BANK001&loan_type=RETAIL&page=1&page_size=2"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["total"]     == 5
        assert data["pages"]     == 3


# ── Profiling endpoint ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfilingEndpoint:

    def test_tenant_id_eksik_400(self, client):
        resp = client.get("/internal/profiling/?loan_type=RETAIL")
        assert resp.status_code == 400

    def test_kayit_yoksa_404(self, client, tenant):
        resp = client.get(
            "/internal/profiling/?tenant_id=BANK001&loan_type=RETAIL"
        )
        assert resp.status_code == 404

    def test_profiling_yaniti(self, client, dolu_db):
        resp = client.get(
            "/internal/profiling/?tenant_id=BANK001&loan_type=RETAIL"
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["toplam_kayit"]         == 5
        assert "faiz_istatistikleri"         in data
        assert "tutar_istatistikleri"        in data
        assert "veri_kalitesi"               in data
        assert "durum_dagilimi"              in data

        # Faiz kontrolü
        assert float(data["faiz_istatistikleri"]["min"]) == 45.0
        assert float(data["faiz_istatistikleri"]["max"]) == 45.0
