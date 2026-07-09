use chrono::NaiveDate;

pub fn dolu_mu(deger: &str) -> bool {
    !deger.trim().is_empty()
}

pub fn sayi_gecerli_mi(deger: &str, min: f64, max: f64) -> bool {
    match deger.trim().parse::<f64>() {
        Ok(sayi) => sayi >= min && sayi <= max,
        Err(_) => false,
    }
}

pub fn tarih_gecerli_mi(deger: &str) -> bool {
    let temiz = deger.trim();
    if NaiveDate::parse_from_str(temiz, "%Y%m%d").is_ok() {
        return true;
    }
    if NaiveDate::parse_from_str(temiz, "%Y-%m-%d").is_ok() {
        return true;
    }
    false
}

pub fn enum_gecerli_mi(deger: &str, izinliler: &[&str]) -> bool {
    izinliler.contains(&deger.trim())
}

#[cfg(test)]
mod tests {
    use super::*;

    

    #[test]
    fn dolu_mu_bos_string_false() {
        assert!(!dolu_mu(""));
    }

    #[test]
    fn dolu_mu_sadece_bosluk_false() {
        assert!(!dolu_mu("   "));
    }

    #[test]
    fn dolu_mu_dolu_deger_true() {
        assert!(dolu_mu("LOAN_001"));
    }

    #[test]
    fn dolu_mu_bosluklu_dolu_deger_true() {
        assert!(dolu_mu("  LOAN_001  "));
    }

    

    #[test]
    fn sayi_aralik_icinde_gecerli() {
        assert!(sayi_gecerli_mi("50.5",  0.0, 1000.0));
        assert!(sayi_gecerli_mi("0",     0.0, 1000.0));
        assert!(sayi_gecerli_mi("1000",  0.0, 1000.0));
    }

    #[test]
    fn sayi_aralik_disinda_gecersiz() {
        assert!(!sayi_gecerli_mi("1001", 0.0, 1000.0));
        assert!(!sayi_gecerli_mi("-1",   0.0, 1000.0));
    }

    #[test]
    fn sayi_sayi_olmayan_deger_gecersiz() {
        assert!(!sayi_gecerli_mi("abc",  0.0, 1000.0));
        assert!(!sayi_gecerli_mi("",     0.0, 1000.0));
        assert!(!sayi_gecerli_mi("1.2.3",0.0, 1000.0));
    }

    

    #[test]
    fn tarih_yyyymmdd_gecerli() {
        assert!(tarih_gecerli_mi("20250302"));
        assert!(tarih_gecerli_mi("20261231"));
    }

    #[test]
    fn tarih_tireli_format_gecerli() {
        assert!(tarih_gecerli_mi("2025-03-02"));
        assert!(tarih_gecerli_mi("2026-12-31"));
    }

    #[test]
    fn tarih_olmayan_ay_gecersiz() {
        assert!(!tarih_gecerli_mi("20251345")); 
    }

    #[test]
    fn tarih_subat_30_gecersiz() {
        assert!(!tarih_gecerli_mi("20250230")); 
    }

    #[test]
    fn tarih_harf_gecersiz() {
        assert!(!tarih_gecerli_mi("ABC"));
        assert!(!tarih_gecerli_mi(""));
    }

    

    #[test]
    fn enum_listede_var_gecerli() {
        assert!(enum_gecerli_mi("E", &["E", "H"]));
        assert!(enum_gecerli_mi("H", &["E", "H"]));
        assert!(enum_gecerli_mi("A", &["A", "K"]));
        assert!(enum_gecerli_mi("K", &["A", "K"]));
    }

    #[test]
    fn enum_listede_yok_gecersiz() {
        assert!(!enum_gecerli_mi("X",  &["E", "H"]));
        assert!(!enum_gecerli_mi("",   &["E", "H"]));
        assert!(!enum_gecerli_mi("e",  &["E", "H"])); 
    }

    #[test]
    fn enum_bosluklu_deger_trim_edilir() {
        assert!(enum_gecerli_mi("  E  ", &["E", "H"]));
    }
}
