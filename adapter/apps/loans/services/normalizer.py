from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

MUSTERI_TIPI: dict[str, str] = {
    "I": "BIREYSEL",
    "i": "BIREYSEL",
    "BIREYSEL": "BIREYSEL",
    "INDIVIDUAL": "BIREYSEL",
    "RETAIL": "BIREYSEL",
    "C": "KURUMSAL",
    "c": "KURUMSAL",
    "KURUMSAL": "KURUMSAL",
    "CORPORATE": "KURUMSAL",
    "COMMERCIAL": "KURUMSAL",
}

KREDI_DURUMU: dict[str, str] = {
    "A": "AKTIF",
    "a": "AKTIF",
    "AKTIF": "AKTIF",
    "ACTIVE": "AKTIF",
    "AÇIK": "AKTIF",
    "OPEN": "AKTIF",
    "K": "KAPALI",
    "k": "KAPALI",
    "KAPALI": "KAPALI",
    "CLOSED": "KAPALI",
    "N": "GECIKME",
    "n": "GECIKME",
    "GECIKME": "GECIKME",
    "DELINQUENT": "GECIKME",
    "NPL": "GECIKME",
}

TAKSIT_DURUMU: dict[str, str] = {
    "A": "ACIK",
    "a": "ACIK",
    "ACIK": "ACIK",
    "AÇIK": "ACIK",
    "OPEN": "ACIK",
    "K": "KAPALI",
    "k": "KAPALI",
    "KAPALI": "KAPALI",
    "CLOSED": "KAPALI",
    "PAID": "KAPALI",
}


def parse_category(deger: str, harita: dict[str, str]) -> str:
    """
    Ham kategori kodunu standart değere dönüştürür.
    Haritada yoksa orijinal değeri (büyük harf) döndürür.
    Örnek: 'K' → 'KAPALI', 'Kapalı' → 'KAPALI', 'CLOSED' → 'KAPALI'
    """
    temiz = deger.strip()
    return harita.get(temiz) or harita.get(temiz.upper()) or temiz.upper()


def parse_date(deger: str) -> Optional[date]:
    """YYYYMMDD, YYYY-MM-DD veya DD.MM.YYYY → Python date. Geçersizse None."""
    if not deger or not deger.strip():
        return None
    temiz = deger.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(temiz, fmt).date()
        except ValueError:
            continue
    return None


def parse_decimal(deger: str, varsayilan: str = "0") -> Decimal:
    """String → Decimal. Virgülü noktaya çevir. Geçersizse varsayılanı dön."""
    try:
        return Decimal(deger.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal(varsayilan)


def parse_rate(deger: str, varsayilan: str = "0") -> Decimal:
    """
    Faiz oranını Decimal'a dönüştürür.
    Desteklenen formatlar:
      - '18.5%'   →  Decimal('18.5')   (yüzde işareti çıkar)
      - '0.185'   →  Decimal('0.185')  (ondalik, oldugu gibi bırak)
      - '1850'    →  Decimal('1850')   (ham sayı)
      - '1850bps' →  Decimal('18.5')   (baz puan: 100 bps = 1%)
    """
    if not deger or not deger.strip():
        return Decimal(varsayilan)
    temiz = deger.strip()

    if temiz.lower().endswith("bps"):
        try:
            return Decimal(temiz[:-3].strip()) / 100
        except InvalidOperation:
            return Decimal(varsayilan)

    if temiz.endswith("%"):
        try:
            return Decimal(temiz[:-1].strip().replace(",", "."))
        except InvalidOperation:
            return Decimal(varsayilan)

    return parse_decimal(temiz, varsayilan)


def parse_int(deger: str, varsayilan: int = 0) -> int:
    """String → int. Geçersizse varsayılanı dön."""
    try:
        return int(deger.strip())
    except (ValueError, AttributeError):
        return varsayilan


def normalize_retail_credit(row: dict) -> dict:
    """Bir retail kredi satırını Django model alanlarına uygun tiplere çevirir."""
    return {
        "loan_account_number": row.get("loan_account_number", "").strip(),
        "customer_id": row.get("customer_id", "").strip(),
        "customer_type": parse_category(row.get("customer_type", ""), MUSTERI_TIPI),
        "loan_status_code": parse_category(row.get("loan_status_code", ""), KREDI_DURUMU),
        "days_past_due": parse_int(row.get("days_past_due", "0")),
        "loan_start_date": parse_date(row.get("loan_start_date", "")),
        "final_maturity_date": parse_date(row.get("final_maturity_date", "")),
        "first_payment_date": parse_date(row.get("first_payment_date", "")),
        "loan_closing_date": parse_date(row.get("loan_closing_date", "")),
        "total_installment_count": parse_int(row.get("total_installment_count", "0")),
        "outstanding_installment_count": parse_int(row.get("outstanding_installment_count", "0")),
        "paid_installment_count": parse_int(row.get("paid_installment_count", "0")),
        "grace_period_months": parse_int(row.get("grace_period_months", "0")),
        "installment_frequency": parse_int(row.get("installment_frequency", "1")),
        "original_loan_amount": parse_decimal(row.get("original_loan_amount", "0")),
        "outstanding_principal_balance": parse_decimal(
            row.get("outstanding_principal_balance", "0")
        ),
        "total_interest_amount": parse_decimal(row.get("total_interest_amount", "0")),
        "nominal_interest_rate": parse_rate(row.get("nominal_interest_rate", "0")),
        "kkdf_rate": parse_rate(row.get("kkdf_rate", "0")),
        "kkdf_amount": parse_decimal(row.get("kkdf_amount", "0")),
        "bsmv_rate": parse_rate(row.get("bsmv_rate", "0")),
        "bsmv_amount": parse_decimal(row.get("bsmv_amount", "0")),
        "internal_rating": row.get("internal_rating", "").strip(),
        "external_rating": row.get("external_rating", "").strip(),
        "customer_district_code": row.get("customer_district_code", "").strip(),
        "customer_province_code": row.get("customer_province_code", "").strip(),
        "insurance_included": row.get("insurance_included", "").strip(),
    }


def normalize_commercial_credit(row: dict) -> dict:
    """Bir commercial kredi satırını Django model alanlarına uygun tiplere çevirir."""
    return {
        "loan_account_number": row.get("loan_account_number", "").strip(),
        "customer_id": row.get("customer_id", "").strip(),
        "customer_type": parse_category(row.get("customer_type", ""), MUSTERI_TIPI),
        "loan_status_code": parse_category(row.get("loan_status_code", ""), KREDI_DURUMU),
        "days_past_due": parse_int(row.get("days_past_due", "0")),
        "loan_start_date": parse_date(row.get("loan_start_date", "")),
        "final_maturity_date": parse_date(row.get("final_maturity_date", "")),
        "first_payment_date": parse_date(row.get("first_payment_date", "")),
        "loan_closing_date": parse_date(row.get("loan_closing_date", "")),
        "total_installment_count": parse_int(row.get("total_installment_count", "0")),
        "outstanding_installment_count": parse_int(row.get("outstanding_installment_count", "0")),
        "paid_installment_count": parse_int(row.get("paid_installment_count", "0")),
        "grace_period_months": parse_int(row.get("grace_period_months", "0")),
        "installment_frequency": parse_int(row.get("installment_frequency", "1")),
        "original_loan_amount": parse_decimal(row.get("original_loan_amount", "0")),
        "outstanding_principal_balance": parse_decimal(
            row.get("outstanding_principal_balance", "0")
        ),
        "total_interest_amount": parse_decimal(row.get("total_interest_amount", "0")),
        "nominal_interest_rate": parse_rate(row.get("nominal_interest_rate", "0")),
        "kkdf_rate": parse_rate(row.get("kkdf_rate", "0")),
        "kkdf_amount": parse_decimal(row.get("kkdf_amount", "0")),
        "bsmv_rate": parse_rate(row.get("bsmv_rate", "0")),
        "bsmv_amount": parse_decimal(row.get("bsmv_amount", "0")),
        "internal_rating": row.get("internal_rating", "").strip(),
        "external_rating": row.get("external_rating", "").strip(),
        "loan_product_type": row.get("loan_product_type", "").strip(),
        "loan_status_flag": row.get("loan_status_flag", "").strip(),
        "customer_region_code": row.get("customer_region_code", "").strip(),
        "sector_code": row.get("sector_code", "").strip(),
        "internal_credit_rating": row.get("internal_credit_rating", "").strip(),
        "default_probability": parse_decimal(row.get("default_probability", "")) or None,
        "risk_class": row.get("risk_class", "").strip(),
        "customer_segment": row.get("customer_segment", "").strip(),
    }


def normalize_payment_plan(row: dict) -> dict:
    """
    Ödeme planı satırını Django PaymentPlan model alanlarına uygun tiplere çevirir.
    `credit` FK alanı hariç — o sync_service tarafından set edilir.
    """
    return {
        "installment_number": parse_int(row.get("installment_number", "0")),
        "scheduled_payment_date": parse_date(row.get("scheduled_payment_date", "")),
        "actual_payment_date": parse_date(row.get("actual_payment_date", "")),
        "installment_amount": parse_decimal(row.get("installment_amount", "0")),
        "principal_component": parse_decimal(row.get("principal_component", "0")),
        "interest_component": parse_decimal(row.get("interest_component", "0")),
        "kkdf_component": parse_decimal(row.get("kkdf_component", "0")),
        "bsmv_component": parse_decimal(row.get("bsmv_component", "0")),
        "installment_status": parse_category(row.get("installment_status", ""), TAKSIT_DURUMU),
        "remaining_principal": parse_decimal(row.get("remaining_principal", "0")),
        "remaining_interest": parse_decimal(row.get("remaining_interest", "0")),
        "remaining_kkdf": parse_decimal(row.get("remaining_kkdf", "0")),
        "remaining_bsmv": parse_decimal(row.get("remaining_bsmv", "0")),
    }
