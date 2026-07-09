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
