"""
Validator birim testleri.
Alan doğrulama, tarih, faiz, enum ve cross-field kontrolleri test edilir.
"""

import pytest
from apps.loans.services.validator import (
    validate_retail_credit,
    validate_commercial_credit,
    validate_payment_plan,
)


class TestRetailKrediValidator:

    def test_gecerli_satir(self, retail_gecerli):
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is True
        assert sonuc.hatalar == []

    def test_bos_hesap_no(self, retail_gecerli):
        retail_gecerli["loan_account_number"] = ""
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "loan_account_number" in alanlar

    def test_bos_musteri_id(self, retail_gecerli):
        retail_gecerli["customer_id"] = "  "
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False

    def test_faiz_aralik_disi_yuksek(self, retail_gecerli):
        retail_gecerli["nominal_interest_rate"] = "1500.0"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "nominal_interest_rate" in alanlar

    def test_faiz_negatif(self, retail_gecerli):
        retail_gecerli["nominal_interest_rate"] = "-5.0"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False

    def test_faiz_sayi_degil(self, retail_gecerli):
        retail_gecerli["nominal_interest_rate"] = "yüzde elli"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False

    def test_gecersiz_tarih_yyyymmdd(self, retail_gecerli):
        retail_gecerli["loan_start_date"] = "20251345"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "loan_start_date" in alanlar

    def test_gecersiz_tarih_subat_30(self, retail_gecerli):
        retail_gecerli["loan_start_date"] = "20250230"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False

    def test_gecerli_tarih_tireli_format(self, retail_gecerli):
        retail_gecerli["loan_start_date"] = "2025-03-02"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is True

    def test_gecersiz_sigorta_kodu(self, retail_gecerli):
        retail_gecerli["insurance_included"] = "X"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "insurance_included" in alanlar

    def test_sigorta_h_gecerli(self, retail_gecerli):
        retail_gecerli["insurance_included"] = "H"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is True

    def test_bos_sigorta_gecerli(self, retail_gecerli):
        retail_gecerli["insurance_included"] = ""
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is True

    def test_birden_fazla_hata(self, retail_gecerli):
        retail_gecerli["loan_account_number"] = ""
        retail_gecerli["nominal_interest_rate"] = "9999"
        retail_gecerli["loan_start_date"] = "ABC"
        sonuc = validate_retail_credit(retail_gecerli)
        assert sonuc.gecerli is False
        assert len(sonuc.hatalar) >= 3


class TestCommercialKrediValidator:

    def test_gecerli_satir(self, commercial_gecerli):
        sonuc = validate_commercial_credit(commercial_gecerli)
        assert sonuc.gecerli is True

    def test_bos_zorunlu_alan(self, commercial_gecerli):
        commercial_gecerli["original_loan_amount"] = ""
        sonuc = validate_commercial_credit(commercial_gecerli)
        assert sonuc.gecerli is False

    def test_faiz_aralik_disi(self, commercial_gecerli):
        commercial_gecerli["nominal_interest_rate"] = "2000"
        sonuc = validate_commercial_credit(commercial_gecerli)
        assert sonuc.gecerli is False


class TestOdemePlaniValidator:

    def test_gecerli_satir(self, odeme_plani_gecerli):
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is True

    def test_bos_hesap_no(self, odeme_plani_gecerli):
        odeme_plani_gecerli["loan_account_number"] = ""
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is False

    def test_bos_taksit_tutari(self, odeme_plani_gecerli):
        odeme_plani_gecerli["installment_amount"] = ""
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is False

    def test_negatif_tutar(self, odeme_plani_gecerli):
        odeme_plani_gecerli["installment_amount"] = "-100"
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "installment_amount" in alanlar

    def test_gecersiz_tarih(self, odeme_plani_gecerli):
        odeme_plani_gecerli["scheduled_payment_date"] = "20251345"
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is False

    def test_gecersiz_taksit_status(self, odeme_plani_gecerli):
        odeme_plani_gecerli["installment_status"] = "X"
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is False
        alanlar = [h.alan for h in sonuc.hatalar]
        assert "installment_status" in alanlar

    def test_gecerli_status_a_ve_k(self, odeme_plani_gecerli):
        for durum in ("A", "K"):
            odeme_plani_gecerli["installment_status"] = durum
            sonuc = validate_payment_plan(odeme_plani_gecerli)
            assert sonuc.gecerli is True, f"{durum} geçerli olmalı"

    def test_gercek_odeme_tarihi_bos_olabilir(self, odeme_plani_gecerli):
        odeme_plani_gecerli["actual_payment_date"] = ""
        sonuc = validate_payment_plan(odeme_plani_gecerli)
        assert sonuc.gecerli is True
