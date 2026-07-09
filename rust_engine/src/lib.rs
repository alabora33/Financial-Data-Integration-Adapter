use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

mod validation;
use validation::{dolu_mu, sayi_gecerli_mi, tarih_gecerli_mi, enum_gecerli_mi};

#[pyfunction]
fn validate_row(py: Python<'_>, row: HashMap<String, String>) -> PyResult<PyObject> {
    let get = |key: &str| -> &str {
        row.get(key).map(|s| s.as_str()).unwrap_or("")
    };

    let mut hatalar: Vec<PyObject> = Vec::new();

    
    let zorunlu = [
        "loan_account_number",
        "customer_id",
        "loan_start_date",
        "final_maturity_date",
        "nominal_interest_rate",
        "original_loan_amount",
    ];
    for alan in zorunlu {
        if !dolu_mu(get(alan)) {
            let h = PyDict::new_bound(py);
            h.set_item("alan", alan)?;
            h.set_item("deger", "")?;
            h.set_item("sebep", "Zorunlu alan boş")?;
            hatalar.push(h.into());
        }
    }

    
    let faiz = get("nominal_interest_rate");
    if !faiz.is_empty() && !sayi_gecerli_mi(faiz, 0.0, 1000.0) {
        let h = PyDict::new_bound(py);
        h.set_item("alan", "nominal_interest_rate")?;
        h.set_item("deger", faiz)?;
        h.set_item("sebep", "0-1000 aralığı dışı veya sayı değil")?;
        hatalar.push(h.into());
    }

    
    for alan in ["loan_start_date", "final_maturity_date", "first_payment_date"] {
        let deger = get(alan);
        if !deger.is_empty() && !tarih_gecerli_mi(deger) {
            let h = PyDict::new_bound(py);
            h.set_item("alan", alan)?;
            h.set_item("deger", deger)?;
            h.set_item("sebep", "Geçersiz tarih (YYYYMMDD, YYYY-MM-DD veya GG.AA.YYYY olmalı)")?;
            hatalar.push(h.into());
        }
    }

    
    let sigorta = get("insurance_included");
    if !sigorta.is_empty() && !enum_gecerli_mi(sigorta, &["E", "H"]) {
        let h = PyDict::new_bound(py);
        h.set_item("alan", "insurance_included")?;
        h.set_item("deger", sigorta)?;
        h.set_item("sebep", "E veya H olmalı")?;
        hatalar.push(h.into());
    }

    
    let result = PyDict::new_bound(py);
    result.set_item("gecerli", hatalar.is_empty())?;
    result.set_item("hatalar", hatalar)?;

    Ok(result.into())
}

#[pymodule]
fn rust_validator(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(validate_row, m)?)?;
    Ok(())
}
