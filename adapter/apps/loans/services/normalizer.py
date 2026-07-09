from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


def parse_date(deger: str) -> Optional[date]:
    """YYYYMMDD veya YYYY-MM-DD → Python date. Geçersizse None."""
    if not deger or not deger.strip():
        return None
    temiz = deger.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
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


def parse_int(deger: str, varsayilan: int = 0) -> int:
    """String → int. Geçersizse varsayılanı dön."""
    try:
        return int(deger.strip())
    except (ValueError, AttributeError):
        return varsayilan


def normalize_retail_credit(row: dict) -> dict:
    """Bir retail kredi satırını Django model alanlarına uygun tiplere çevirir."""
    return {
        "loan_account_number":          row.get("loan_account_number", "").strip(),
        "customer_id":                  row.get("customer_id", "").strip(),
        "customer_type":                row.get("customer_type", "").strip(),
        "loan_status_code":             row.get("loan_status_code", "").strip(),
        "days_past_due":                parse_int(row.get("days_past_due", "0")),
        "loan_start_date":              parse_date(row.get("loan_start_date", "")),
        "final_maturity_date":          parse_date(row.get("final_maturity_date", "")),
        "first_payment_date":           parse_date(row.get("first_payment_date", "")),
        "loan_closing_date":            parse_date(row.get("loan_closing_date", "")),
        "total_installment_count":      parse_int(row.get("total_installment_count", "0")),
        "outstanding_installment_count":parse_int(row.get("outstanding_installment_count", "0")),
        "paid_installment_count":       parse_int(row.get("paid_installment_count", "0")),
        "grace_period_months":          parse_int(row.get("grace_period_months", "0")),
        "installment_frequency":        parse_int(row.get("installment_frequency", "1")),
        "original_loan_amount":         parse_decimal(row.get("original_loan_amount", "0")),
        "outstanding_principal_balance":parse_decimal(row.get("outstanding_principal_balance", "0")),
        "total_interest_amount":        parse_decimal(row.get("total_interest_amount", "0")),
        "nominal_interest_rate":        parse_decimal(row.get("nominal_interest_rate", "0")),
        "kkdf_rate":                    parse_decimal(row.get("kkdf_rate", "0")),
        "kkdf_amount":                  parse_decimal(row.get("kkdf_amount", "0")),
        "bsmv_rate":                    parse_decimal(row.get("bsmv_rate", "0")),
        "bsmv_amount":                  parse_decimal(row.get("bsmv_amount", "0")),
        "internal_rating":              row.get("internal_rating", "").strip(),
        "external_rating":              row.get("external_rating", "").strip(),
        "customer_district_code":       row.get("customer_district_code", "").strip(),
        "customer_province_code":       row.get("customer_province_code", "").strip(),
        "insurance_included":           row.get("insurance_included", "").strip(),
    }


def normalize_commercial_credit(row: dict) -> dict:
    """Bir commercial kredi satırını Django model alanlarına uygun tiplere çevirir."""
    return {
        "loan_account_number":          row.get("loan_account_number", "").strip(),
        "customer_id":                  row.get("customer_id", "").strip(),
        "customer_type":                row.get("customer_type", "").strip(),
        "loan_status_code":             row.get("loan_status_code", "").strip(),
        "days_past_due":                parse_int(row.get("days_past_due", "0")),
        "loan_start_date":              parse_date(row.get("loan_start_date", "")),
        "final_maturity_date":          parse_date(row.get("final_maturity_date", "")),
        "first_payment_date":           parse_date(row.get("first_payment_date", "")),
        "loan_closing_date":            parse_date(row.get("loan_closing_date", "")),
        "total_installment_count":      parse_int(row.get("total_installment_count", "0")),
        "outstanding_installment_count":parse_int(row.get("outstanding_installment_count", "0")),
        "paid_installment_count":       parse_int(row.get("paid_installment_count", "0")),
        "grace_period_months":          parse_int(row.get("grace_period_months", "0")),
        "installment_frequency":        parse_int(row.get("installment_frequency", "1")),
        "original_loan_amount":         parse_decimal(row.get("original_loan_amount", "0")),
        "outstanding_principal_balance":parse_decimal(row.get("outstanding_principal_balance", "0")),
        "total_interest_amount":        parse_decimal(row.get("total_interest_amount", "0")),
        "nominal_interest_rate":        parse_decimal(row.get("nominal_interest_rate", "0")),
        "kkdf_rate":                    parse_decimal(row.get("kkdf_rate", "0")),
        "kkdf_amount":                  parse_decimal(row.get("kkdf_amount", "0")),
        "bsmv_rate":                    parse_decimal(row.get("bsmv_rate", "0")),
        "bsmv_amount":                  parse_decimal(row.get("bsmv_amount", "0")),
        "internal_rating":              row.get("internal_rating", "").strip(),
        "external_rating":              row.get("external_rating", "").strip(),
        # Commercial'a özgü
        "loan_product_type":            row.get("loan_product_type", "").strip(),
        "loan_status_flag":             row.get("loan_status_flag", "").strip(),
        "customer_region_code":         row.get("customer_region_code", "").strip(),
        "sector_code":                  row.get("sector_code", "").strip(),
        "internal_credit_rating":       row.get("internal_credit_rating", "").strip(),
        "default_probability":          parse_decimal(row.get("default_probability", "")) or None,
        "risk_class":                   row.get("risk_class", "").strip(),
        "customer_segment":             row.get("customer_segment", "").strip(),
    }
