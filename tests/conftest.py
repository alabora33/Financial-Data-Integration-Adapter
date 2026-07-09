"""
Ortak fixture'lar ve Django test ortamı.
POSTGRES_HOST set edilmediği için SQLite fallback devreye girer.
"""

import pytest


@pytest.fixture
def retail_gecerli():
    return {
        "loan_account_number": "LOAN_000001",
        "customer_id": "CUST_00001",
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
        "total_interest_amount": "900.00",
        "kkdf_rate": "15.00",
        "kkdf_amount": "135.00",
        "bsmv_rate": "10.00",
        "bsmv_amount": "90.00",
        "grace_period_months": "0",
        "installment_frequency": "1",
        "loan_start_date": "20250302",
        "loan_closing_date": "",
        "insurance_included": "E",
        "customer_district_code": "DISTRICT_A",
        "customer_province_code": "PROVINCE_1",
        "internal_rating": "3",
        "external_rating": "1200",
    }


@pytest.fixture
def commercial_gecerli():
    return {
        "loan_account_number": "LOAN_C00001",
        "customer_id": "CUST_C0001",
        "customer_type": "C",
        "loan_status_code": "A",
        "loan_product_type": "TERM_LOAN",
        "loan_status_flag": "N",
        "days_past_due": "0",
        "final_maturity_date": "20270615",
        "total_installment_count": "24",
        "outstanding_installment_count": "20",
        "paid_installment_count": "4",
        "first_payment_date": "20250715",
        "original_loan_amount": "500000",
        "outstanding_principal_balance": "420000",
        "nominal_interest_rate": "38.50",
        "total_interest_amount": "15000.00",
        "kkdf_rate": "15.00",
        "kkdf_amount": "2250.00",
        "bsmv_rate": "10.00",
        "bsmv_amount": "1500.00",
        "grace_period_months": "0",
        "installment_frequency": "1",
        "loan_start_date": "20250615",
        "loan_closing_date": "",
        "customer_region_code": "REGION_1",
        "sector_code": "MANUFACTURING",
        "internal_credit_rating": "BB+",
        "default_probability": "0.025",
        "risk_class": "STANDARD",
        "customer_segment": "CORPORATE",
        "internal_rating": "2",
        "external_rating": "850",
    }


@pytest.fixture
def odeme_plani_gecerli():
    return {
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


@pytest.fixture
def tenant(db):
    from apps.loans.models import Tenant

    return Tenant.objects.create(bank_code="BANK001", name="Test Bankası")


@pytest.fixture
def kredi_kaydi(tenant):
    from apps.loans.models import CreditRecord
    from decimal import Decimal
    import datetime

    return CreditRecord.objects.create(
        tenant=tenant,
        loan_type="RETAIL",
        loan_account_number="LOAN_000001",
        customer_id="CUST_00001",
        customer_type="I",
        loan_status_code="A",
        loan_start_date=datetime.date(2025, 3, 2),
        final_maturity_date=datetime.date(2026, 3, 2),
        original_loan_amount=Decimal("50000"),
        outstanding_principal_balance=Decimal("38000"),
        nominal_interest_rate=Decimal("45.00"),
        total_interest_amount=Decimal("900"),
    )
