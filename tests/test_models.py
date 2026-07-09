"""
Django model testleri.
ORM davranışları, unique_together kısıtları ve FK cascade test edilir.
"""
import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError

from apps.loans.models import Tenant, CreditRecord, PaymentPlan, SyncLog


@pytest.mark.django_db
class TestTenantModel:

    def test_tenant_olusturma(self):
        t = Tenant.objects.create(bank_code="BANKTEST", name="Test Bankası")
        assert t.pk is not None
        assert str(t) == "BANKTEST"

    def test_bank_code_unique(self):
        Tenant.objects.create(bank_code="BANKDUP")
        with pytest.raises(IntegrityError):
            Tenant.objects.create(bank_code="BANKDUP")

    def test_get_or_create_ikinci_kez_olusturmaz(self):
        t1, created1 = Tenant.objects.get_or_create(bank_code="BANKGOC")
        t2, created2 = Tenant.objects.get_or_create(bank_code="BANKGOC")
        assert created1 is True
        assert created2 is False
        assert t1.pk == t2.pk


@pytest.mark.django_db
class TestCreditRecordModel:

    def test_kredi_kaydi_olusturma(self, tenant):
        cr = CreditRecord.objects.create(
            tenant=tenant,
            loan_type="RETAIL",
            loan_account_number="LOAN_TEST",
            customer_id="CUST_TEST",
            customer_type="I",
            loan_status_code="A",
            loan_start_date=datetime.date(2025, 1, 1),
            final_maturity_date=datetime.date(2026, 1, 1),
            original_loan_amount=Decimal("10000"),
            outstanding_principal_balance=Decimal("8000"),
            nominal_interest_rate=Decimal("40.00"),
            total_interest_amount=Decimal("400"),
        )
        assert cr.pk is not None
        assert str(cr) == "LOAN_TEST (RETAIL)"

    def test_unique_together_ihlali(self, tenant):
        kwargs = dict(
            tenant=tenant,
            loan_type="RETAIL",
            loan_account_number="LOAN_DUP",
            customer_id="C",
            customer_type="I",
            loan_status_code="A",
            loan_start_date=datetime.date(2025, 1, 1),
            final_maturity_date=datetime.date(2026, 1, 1),
            original_loan_amount=Decimal("1"),
            outstanding_principal_balance=Decimal("1"),
            nominal_interest_rate=Decimal("1"),
            total_interest_amount=Decimal("1"),
        )
        CreditRecord.objects.create(**kwargs)
        with pytest.raises(IntegrityError):
            CreditRecord.objects.create(**kwargs)

    def test_farkli_loan_type_ayni_hesap_no(self, tenant):
        """Aynı hesap no farklı loan_type ile oluşturulabilir."""
        base = dict(
            tenant=tenant,
            loan_account_number="LOAN_MULTI",
            customer_id="C",
            customer_type="I",
            loan_status_code="A",
            loan_start_date=datetime.date(2025, 1, 1),
            final_maturity_date=datetime.date(2026, 1, 1),
            original_loan_amount=Decimal("1"),
            outstanding_principal_balance=Decimal("1"),
            nominal_interest_rate=Decimal("1"),
            total_interest_amount=Decimal("1"),
        )
        CreditRecord.objects.create(loan_type="RETAIL",     **base)
        CreditRecord.objects.create(loan_type="COMMERCIAL", **base)
        assert CreditRecord.objects.filter(
            tenant=tenant, loan_account_number="LOAN_MULTI"
        ).count() == 2

    def test_commercial_alanlari_null_olabilir(self, tenant):
        cr = CreditRecord.objects.create(
            tenant=tenant,
            loan_type="RETAIL",
            loan_account_number="LOAN_NULL",
            customer_id="C",
            customer_type="I",
            loan_status_code="A",
            loan_start_date=datetime.date(2025, 1, 1),
            final_maturity_date=datetime.date(2026, 1, 1),
            original_loan_amount=Decimal("1"),
            outstanding_principal_balance=Decimal("1"),
            nominal_interest_rate=Decimal("1"),
            total_interest_amount=Decimal("1"),
        )
        assert cr.sector_code    == ""
        assert cr.default_probability is None


@pytest.mark.django_db
class TestPaymentPlanModel:

    def test_odeme_plani_olusturma(self, kredi_kaydi):
        pp = PaymentPlan.objects.create(
            credit=kredi_kaydi,
            installment_number=1,
            scheduled_payment_date=datetime.date(2025, 4, 2),
            installment_amount=Decimal("4583.33"),
            principal_component=Decimal("4166.67"),
            interest_component=Decimal("375.00"),
            installment_status="K",
        )
        assert pp.pk is not None
        assert "LOAN_000001" in str(pp)

    def test_kredi_silinince_planlar_da_silinir(self, kredi_kaydi):
        PaymentPlan.objects.create(
            credit=kredi_kaydi,
            installment_number=1,
            scheduled_payment_date=datetime.date(2025, 4, 2),
            installment_amount=Decimal("100"),
            principal_component=Decimal("90"),
            interest_component=Decimal("10"),
            installment_status="A",
        )
        kredi_id = kredi_kaydi.pk
        kredi_kaydi.delete()
        assert PaymentPlan.objects.filter(credit_id=kredi_id).count() == 0

    def test_unique_together_taksit(self, kredi_kaydi):
        kwargs = dict(
            credit=kredi_kaydi,
            installment_number=1,
            scheduled_payment_date=datetime.date(2025, 4, 2),
            installment_amount=Decimal("100"),
            principal_component=Decimal("90"),
            interest_component=Decimal("10"),
            installment_status="A",
        )
        PaymentPlan.objects.create(**kwargs)
        with pytest.raises(IntegrityError):
            PaymentPlan.objects.create(**kwargs)


@pytest.mark.django_db
class TestSyncLogModel:

    def test_sync_log_olusturma(self, tenant):
        log = SyncLog.objects.create(
            tenant=tenant,
            loan_type="RETAIL",
            status="PENDING",
        )
        assert log.pk is not None
        assert log.status == "PENDING"
        assert log.sync_finished_at is None

    def test_sync_log_str(self, tenant):
        log = SyncLog.objects.create(
            tenant=tenant,
            loan_type="COMMERCIAL",
            status="SUCCESS",
        )
        assert "BANK001" in str(log)
        assert "COMMERCIAL" in str(log)
