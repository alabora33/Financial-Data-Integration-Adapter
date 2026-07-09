from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import List


@dataclass
class ValidationError:
    alan: str
    deger: str
    sebep: str


@dataclass
class ValidationResult:
    gecerli: bool
    hatalar: List[ValidationError] = dc_field(default_factory=list)


def _tarih_gecerli_mi(deger: str) -> bool:
    """YYYYMMDD veya YYYY-MM-DD formatında gerçek bir tarih mi?"""
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            datetime.strptime(deger.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def validate_retail_credit(row: dict) -> ValidationResult:
    hatalar = []

    # 1. Varlık kontrolü — zorunlu alanlar boş olamaz
    zorunlu = ["loan_account_number", "customer_id", "loan_start_date",
               "final_maturity_date", "nominal_interest_rate", "original_loan_amount"]
    for alan in zorunlu:
        if not row.get(alan, "").strip():
            hatalar.append(ValidationError(alan, "", "Zorunlu alan boş"))

    # 2. Sayı + aralık kontrolü
    faiz = row.get("nominal_interest_rate", "").strip()
    if faiz:
        try:
            v = float(faiz)
            if not (0.0 <= v <= 1000.0):
                hatalar.append(ValidationError("nominal_interest_rate", faiz, "0–1000 aralığı dışı"))
        except ValueError:
            hatalar.append(ValidationError("nominal_interest_rate", faiz, "Sayı değil"))

    # 3. Tarih kontrolü
    for alan in ["loan_start_date", "final_maturity_date", "first_payment_date"]:
        deger = row.get(alan, "").strip()
        if deger and not _tarih_gecerli_mi(deger):
            hatalar.append(ValidationError(alan, deger, "Geçersiz tarih formatı"))

    # 4. Enum kontrolü
    sigorta = row.get("insurance_included", "").strip()
    if sigorta and sigorta not in ("E", "H"):
        hatalar.append(ValidationError("insurance_included", sigorta, "E veya H olmalı"))

    return ValidationResult(gecerli=len(hatalar) == 0, hatalar=hatalar)


def validate_commercial_credit(row: dict) -> ValidationResult:
    hatalar = []

    zorunlu = ["loan_account_number", "customer_id", "loan_start_date",
               "final_maturity_date", "nominal_interest_rate", "original_loan_amount"]
    for alan in zorunlu:
        if not row.get(alan, "").strip():
            hatalar.append(ValidationError(alan, "", "Zorunlu alan boş"))

    faiz = row.get("nominal_interest_rate", "").strip()
    if faiz:
        try:
            v = float(faiz)
            if not (0.0 <= v <= 1000.0):
                hatalar.append(ValidationError("nominal_interest_rate", faiz, "0–1000 aralığı dışı"))
        except ValueError:
            hatalar.append(ValidationError("nominal_interest_rate", faiz, "Sayı değil"))

    for alan in ["loan_start_date", "final_maturity_date"]:
        deger = row.get(alan, "").strip()
        if deger and not _tarih_gecerli_mi(deger):
            hatalar.append(ValidationError(alan, deger, "Geçersiz tarih formatı"))

    return ValidationResult(gecerli=len(hatalar) == 0, hatalar=hatalar)
