from dataclasses import dataclass, field as dc_field
from datetime import datetime
from typing import List

try:
    import rust_validator as _rust
    _USE_RUST = True
except ImportError:
    _USE_RUST = False


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
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            datetime.strptime(deger.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


# ── Kredi doğrulama ───────────────────────────────────────────────────────────

def _python_validate(row: dict, loan_type: str) -> ValidationResult:
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

    for alan in ["loan_start_date", "final_maturity_date", "first_payment_date"]:
        deger = row.get(alan, "").strip()
        if deger and not _tarih_gecerli_mi(deger):
            hatalar.append(ValidationError(alan, deger, "Geçersiz tarih formatı"))

    if loan_type == "RETAIL":
        sigorta = row.get("insurance_included", "").strip()
        if sigorta and sigorta not in ("E", "H"):
            hatalar.append(ValidationError("insurance_included", sigorta, "E veya H olmalı"))

    return ValidationResult(gecerli=len(hatalar) == 0, hatalar=hatalar)


def _rust_validate(row: dict) -> ValidationResult:
    str_row = {k: str(v) if v is not None else "" for k, v in row.items()}
    sonuc = _rust.validate_row(str_row)
    hatalar = [ValidationError(h["alan"], h["deger"], h["sebep"]) for h in sonuc["hatalar"]]
    return ValidationResult(gecerli=sonuc["gecerli"], hatalar=hatalar)


def validate_retail_credit(row: dict) -> ValidationResult:
    if _USE_RUST:
        return _rust_validate(row)
    return _python_validate(row, "RETAIL")


def validate_commercial_credit(row: dict) -> ValidationResult:
    return _python_validate(row, "COMMERCIAL")


# ── Ödeme planı doğrulama ─────────────────────────────────────────────────────

def validate_payment_plan(row: dict) -> ValidationResult:
    """
    Ödeme planı satırı doğrulama:
    - loan_account_number, installment_number, scheduled_payment_date zorunlu
    - installment_amount, principal_component sayı ve >= 0
    - installment_status: A (Açık) veya K (Kapalı)
    - scheduled_payment_date geçerli tarih
    """
    hatalar = []

    # 1. Varlık
    zorunlu = ["loan_account_number", "installment_number",
               "scheduled_payment_date", "installment_amount"]
    for alan in zorunlu:
        if not row.get(alan, "").strip():
            hatalar.append(ValidationError(alan, "", "Zorunlu alan boş"))

    # 2. Sayı kontrolü
    for alan in ["installment_amount", "principal_component",
                 "interest_component", "remaining_principal"]:
        deger = row.get(alan, "").strip()
        if deger:
            try:
                v = float(deger)
                if v < 0:
                    hatalar.append(ValidationError(alan, deger, "Negatif değer olamaz"))
            except ValueError:
                hatalar.append(ValidationError(alan, deger, "Sayı değil"))

    # 3. Tarih kontrolü
    for alan in ["scheduled_payment_date", "actual_payment_date"]:
        deger = row.get(alan, "").strip()
        if deger and not _tarih_gecerli_mi(deger):
            hatalar.append(ValidationError(alan, deger, "Geçersiz tarih formatı"))

    # 4. Enum: installment_status A veya K
    status = row.get("installment_status", "").strip()
    if status and status not in ("A", "K"):
        hatalar.append(ValidationError("installment_status", status, "A (Açık) veya K (Kapalı) olmalı"))

    return ValidationResult(gecerli=len(hatalar) == 0, hatalar=hatalar)



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
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            datetime.strptime(deger.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _python_validate(row: dict, loan_type: str) -> ValidationResult:
    """Rust yoksa devreye giren Python implementasyonu."""
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

    for alan in ["loan_start_date", "final_maturity_date", "first_payment_date"]:
        deger = row.get(alan, "").strip()
        if deger and not _tarih_gecerli_mi(deger):
            hatalar.append(ValidationError(alan, deger, "Geçersiz tarih formatı"))

    if loan_type == "RETAIL":
        sigorta = row.get("insurance_included", "").strip()
        if sigorta and sigorta not in ("E", "H"):
            hatalar.append(ValidationError("insurance_included", sigorta, "E veya H olmalı"))

    return ValidationResult(gecerli=len(hatalar) == 0, hatalar=hatalar)


def _rust_validate(row: dict) -> ValidationResult:
    """Rust modülünü çağır, sonucu ValidationResult'a çevir."""
    # Rust fonksiyonu tüm değerlerin string olmasını bekler
    str_row = {k: str(v) if v is not None else "" for k, v in row.items()}
    sonuc = _rust.validate_row(str_row)
    hatalar = [
        ValidationError(h["alan"], h["deger"], h["sebep"])
        for h in sonuc["hatalar"]
    ]
    return ValidationResult(gecerli=sonuc["gecerli"], hatalar=hatalar)


def validate_retail_credit(row: dict) -> ValidationResult:
    if _USE_RUST:
        return _rust_validate(row)
    return _python_validate(row, "RETAIL")


def validate_commercial_credit(row: dict) -> ValidationResult:
    # Commercial için şimdilik Python (Rust tarafı genişletilebilir)
    return _python_validate(row, "COMMERCIAL")

