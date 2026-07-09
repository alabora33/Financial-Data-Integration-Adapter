"""
Normalizer birim testleri.
Tip dönüşümleri ve edge case'ler test edilir.
"""

import datetime
from decimal import Decimal

import pytest
from apps.loans.services.normalizer import (
    parse_date,
    parse_decimal,
    parse_int,
    parse_rate,
    normalize_retail_credit,
    normalize_payment_plan,
)


class TestParseDate:

    def test_yyyymmdd_format(self):
        assert parse_date("20250302") == datetime.date(2025, 3, 2)

    def test_tireli_format(self):
        assert parse_date("2025-03-02") == datetime.date(2025, 3, 2)

    def test_bos_string(self):
        assert parse_date("") is None

    def test_none(self):
        assert parse_date(None) is None

    def test_sadece_bosluk(self):
        assert parse_date("   ") is None

    def test_olmayan_tarih(self):
        assert parse_date("20251345") is None

    def test_subatta_30_gun_yok(self):
        assert parse_date("20250230") is None

    def test_gecersiz_format(self):
        assert parse_date("ABC") is None

    def test_on_dort_aralik(self):
        assert parse_date("20251214") == datetime.date(2025, 12, 14)


class TestParseDecimal:

    def test_normal_sayi(self):
        assert parse_decimal("55.47") == Decimal("55.47")

    def test_virgullu_format(self):
        assert parse_decimal("55,47") == Decimal("55.47")

    def test_tam_sayi(self):
        assert parse_decimal("100") == Decimal("100")

    def test_sifir(self):
        assert parse_decimal("0") == Decimal("0")

    def test_bos_string_varsayilan(self):
        assert parse_decimal("") == Decimal("0")
        assert parse_decimal("", "99") == Decimal("99")

    def test_gecersiz_deger_varsayilan(self):
        assert parse_decimal("abc") == Decimal("0")

    def test_bosluklu_deger(self):
        assert parse_decimal("  45.50  ") == Decimal("45.50")


class TestParseInt:

    def test_normal(self):
        assert parse_int("12") == 12

    def test_bos(self):
        assert parse_int("") == 0
        assert parse_int("", 99) == 99

    def test_gecersiz(self):
        assert parse_int("abc") == 0

    def test_bosluklu(self):
        assert parse_int("  7  ") == 7


class TestParseRate:
    """Faiz oranı dönüşümü — dokümanda açıkça belirtilen 3 format."""

    def test_yuzde_format(self):
        assert parse_rate("18.5%") == Decimal("18.5")

    def test_yuzde_virgul_ayrac(self):
        assert parse_rate("18,5%") == Decimal("18.5")

    def test_bps_format(self):
        assert parse_rate("1850bps") == Decimal("18.5")

    def test_bps_buyuk_harf(self):
        assert parse_rate("1850BPS") == Decimal("18.5")

    def test_ham_sayi_oldugu_gibi(self):
        assert parse_rate("45.00") == Decimal("45.00")

    def test_bos_varsayilan_sifir(self):
        assert parse_rate("") == Decimal("0")
        assert parse_rate("   ") == Decimal("0")

    def test_gecersiz_deger_varsayilan(self):
        assert parse_rate("abc") == Decimal("0")


class TestNormalizeRetailCredit:

    def test_temel_alanlar(self, retail_gecerli):
        sonuc = normalize_retail_credit(retail_gecerli)
        assert sonuc["loan_account_number"] == "LOAN_000001"
        assert sonuc["customer_id"] == "CUST_00001"
        assert sonuc["customer_type"] == "BIREYSEL"

    def test_tarih_donusumu(self, retail_gecerli):
        sonuc = normalize_retail_credit(retail_gecerli)
        assert sonuc["loan_start_date"] == datetime.date(2025, 3, 2)
        assert isinstance(sonuc["loan_start_date"], datetime.date)

    def test_decimal_donusumu(self, retail_gecerli):
        sonuc = normalize_retail_credit(retail_gecerli)
        assert isinstance(sonuc["original_loan_amount"], Decimal)
        assert isinstance(sonuc["nominal_interest_rate"], Decimal)
        assert sonuc["nominal_interest_rate"] == Decimal("45.00")

    def test_int_donusumu(self, retail_gecerli):
        sonuc = normalize_retail_credit(retail_gecerli)
        assert isinstance(sonuc["total_installment_count"], int)
        assert sonuc["total_installment_count"] == 12

    def test_bos_tarih_none_dondu(self, retail_gecerli):
        retail_gecerli["loan_closing_date"] = ""
        sonuc = normalize_retail_credit(retail_gecerli)
        assert sonuc["loan_closing_date"] is None

    def test_bosluk_temizleme(self, retail_gecerli):
        retail_gecerli["loan_account_number"] = "  LOAN_000001  "
        sonuc = normalize_retail_credit(retail_gecerli)
        assert sonuc["loan_account_number"] == "LOAN_000001"

    def test_kategori_i_bireysel(self, retail_gecerli):
        retail_gecerli["customer_type"] = "I"
        assert normalize_retail_credit(retail_gecerli)["customer_type"] == "BIREYSEL"

    def test_kategori_c_kurumsal(self, retail_gecerli):
        retail_gecerli["customer_type"] = "C"
        assert normalize_retail_credit(retail_gecerli)["customer_type"] == "KURUMSAL"

    def test_kategori_kredi_durumu_a_aktif(self, retail_gecerli):
        retail_gecerli["loan_status_code"] = "A"
        assert normalize_retail_credit(retail_gecerli)["loan_status_code"] == "AKTIF"

    def test_kategori_kredi_durumu_varyant(self, retail_gecerli):
        retail_gecerli["loan_status_code"] = "Active"
        assert normalize_retail_credit(retail_gecerli)["loan_status_code"] == "AKTIF"


class TestNormalizePaymentPlan:

    def test_temel_alanlar(self, odeme_plani_gecerli):
        sonuc = normalize_payment_plan(odeme_plani_gecerli)
        assert sonuc["installment_number"] == 1
        assert sonuc["installment_status"] == "KAPALI"

    def test_tarih_donusumu(self, odeme_plani_gecerli):
        sonuc = normalize_payment_plan(odeme_plani_gecerli)
        assert sonuc["scheduled_payment_date"] == datetime.date(2025, 4, 2)
        assert isinstance(sonuc["scheduled_payment_date"], datetime.date)

    def test_decimal_tutarlar(self, odeme_plani_gecerli):
        sonuc = normalize_payment_plan(odeme_plani_gecerli)
        assert isinstance(sonuc["installment_amount"], Decimal)
        assert sonuc["installment_amount"] == Decimal("4583.33")

    def test_bos_odeme_tarihi_none(self, odeme_plani_gecerli):
        odeme_plani_gecerli["actual_payment_date"] = ""
        sonuc = normalize_payment_plan(odeme_plani_gecerli)
        assert sonuc["actual_payment_date"] is None
