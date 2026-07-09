mod validation;

use std::fs;
use std::collections::HashMap;
use validation::{dolu_mu, sayi_gecerli_mi, tarih_gecerli_mi, enum_gecerli_mi};

struct Alan {
    gecerli: u32,
    hatali: u32,
}

impl Alan {
    fn yeni() -> Self {
        Alan { gecerli: 0, hatali: 0 }
    }

    fn guncelle(&mut self, gecerli_mi: bool) {
        if gecerli_mi {
            self.gecerli += 1;
        } else {
            self.hatali += 1;
        }
    }
}

fn yazdir(ad: &str, alan: &Alan) {
    println!("{} -> gecerli: {}, hatali: {}", ad, alan.gecerli, alan.hatali);
}

fn main() {
    let yol = "/home/alibora/projects/teamsec-adapter/sample_data/teamsec-interview-data/retail_credit_masked.csv";

    let icerik = fs::read_to_string(yol)
        .expect("CSV okunamadi");

    let mut satirlar = icerik.lines();

    let baslik_satiri = satirlar.next().expect("Dosya bos");
    let basliklar: Vec<&str> = baslik_satiri.split(';').collect();
    println!("Sutun sayisi: {}", basliklar.len());

    let indeks: HashMap<&str, usize> = basliklar
        .iter()
        .enumerate()
        .map(|(i, ad)| (*ad, i))
        .collect();

    let mut loan_id    = Alan::yeni();
    let mut faiz       = Alan::yeni();
    let mut tarih      = Alan::yeni();
    let mut sigorta    = Alan::yeni();

    for satir in satirlar {
        let hucreler: Vec<&str> = satir.split(';').collect();
        if hucreler.len() < basliklar.len() {
            continue; 
        }

        loan_id.guncelle(
            dolu_mu(hucreler[indeks["loan_account_number"]])
        );
        faiz.guncelle(
            sayi_gecerli_mi(hucreler[indeks["nominal_interest_rate"]], 0.0, 1000.0)
        );
        tarih.guncelle(
            tarih_gecerli_mi(hucreler[indeks["loan_start_date"]])
        );
        sigorta.guncelle(
            enum_gecerli_mi(hucreler[indeks["insurance_included"]], &["E", "H"])
        );
    }

    println!();
    yazdir("loan_account_number  [dolu_mu]", &loan_id);
    yazdir("nominal_interest_rate [sayi]  ", &faiz);
    yazdir("loan_start_date      [tarih]  ", &tarih);
    yazdir("insurance_included   [enum]   ", &sigorta);
}
