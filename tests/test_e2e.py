"""
E2E / Docker entegrasyon testleri.

Tüm servisler `docker compose up` ile çalışırken tam akışı doğrular:
  health → auth (login/register) → sync → data → profiling

Servisler ayakta değilse testler otomatik olarak atlanır.

Çalıştırma:
    docker compose up -d
    pytest tests/test_e2e.py -v
"""
import uuid

import httpx
import pytest

API_URL = "http://localhost:8000"
_TIMEOUT = 30.0
_SYNC_TIMEOUT = 300.0  # sync uzun sürebilir


def _full_stack_reachable() -> bool:
    """
    API + adapter + DB'nin tamamının çalıştığını doğrular.
    API /health + adapter proxy üzerinden basit bir data çağrısı dener.
    """
    try:
        # API health
        resp = httpx.get(f"{API_URL}/health", timeout=3.0)
        if resp.status_code != 200:
            return False
        # Adapter proxy kontrolü: token al, data endpoint'ini çağır
        tok = httpx.post(
            f"{API_URL}/auth/token",
            data={"username": "admin", "password": "admin"},
            timeout=3.0,
        )
        if tok.status_code != 200:
            return False
        headers = {"Authorization": f"Bearer {tok.json()['access_token']}"}
        data = httpx.get(
            f"{API_URL}/api/data",
            params={"tenant_id": "BANK001", "loan_type": "RETAIL", "page_size": 1},
            headers=headers,
            timeout=5.0,
        )
        return data.status_code in (200, 404)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _full_stack_reachable(),
    reason=(
        "E2E testleri atlandı — önce `docker compose up` ile servisleri başlatın "
        "(API + adapter + DB gerekli)"
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def admin_token():
    """admin kullanıcısından JWT token alır."""
    resp = httpx.post(
        f"{API_URL}/auth/token",
        data={"username": "admin", "password": "admin"},
        timeout=_TIMEOUT,
    )
    assert resp.status_code == 200, f"Admin login başarısız: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def synced_bank(auth_headers):
    """
    BANK001 / RETAIL sync'ini bir kez tetikler, modül boyunca paylaşır.
    Sync zaten yapılmışsa (veri varsa) yeniden tetiklemez.
    """
    # Önce veri var mı diye bak
    check = httpx.get(
        f"{API_URL}/api/data",
        params={"tenant_id": "BANK001", "loan_type": "RETAIL", "page_size": 1},
        headers=auth_headers,
        timeout=_TIMEOUT,
    )
    if check.status_code == 200 and check.json().get("total", 0) > 0:
        return "BANK001"

    # Veri yoksa sync başlat
    resp = httpx.post(
        f"{API_URL}/api/sync",
        json={"tenant_id": "BANK001", "loan_type": "RETAIL"},
        headers=auth_headers,
        timeout=_SYNC_TIMEOUT,
    )
    assert resp.status_code == 200, f"Sync başarısız: {resp.text}"
    return "BANK001"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestE2EHealth:

    def test_health_ok(self):
        resp = httpx.get(f"{API_URL}/health", timeout=_TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "adapter-api"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestE2EAuth:

    def test_login_admin(self):
        resp = httpx.post(
            f"{API_URL}/auth/token",
            data={"username": "admin", "password": "admin"},
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_yanlis_sifre_401(self):
        resp = httpx.post(
            f"{API_URL}/auth/token",
            data={"username": "admin", "password": "yanlis_sifre_xyz"},
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 401

    def test_register_ve_giris(self):
        """Yeni kullanıcı kayıt → giriş akışı."""
        kullanici = f"e2e_{uuid.uuid4().hex[:8]}"
        # Kayıt
        resp = httpx.post(
            f"{API_URL}/auth/register",
            json={"username": kullanici, "password": "sifre123"},
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 201, f"Kayıt başarısız: {resp.text}"
        # Giriş
        resp2 = httpx.post(
            f"{API_URL}/auth/token",
            data={"username": kullanici, "password": "sifre123"},
            timeout=_TIMEOUT,
        )
        assert resp2.status_code == 200
        assert "access_token" in resp2.json()

    def test_register_kisa_sifre_hata(self):
        resp = httpx.post(
            f"{API_URL}/auth/register",
            json={"username": f"e2e_{uuid.uuid4().hex[:6]}", "password": "12"},
            timeout=_TIMEOUT,
        )
        assert resp.status_code in (400, 409, 422)

    def test_token_olmadan_veri_401(self):
        resp = httpx.get(
            f"{API_URL}/api/data",
            params={"tenant_id": "BANK001", "loan_type": "RETAIL"},
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

class TestE2ESync:

    def test_sync_basarili(self, auth_headers):
        resp = httpx.post(
            f"{API_URL}/api/sync",
            json={"tenant_id": "BANK001", "loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_SYNC_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert data["kredi"]["rows_fetched"] > 0
        assert data["kredi"]["rows_valid"] > 0

    def test_gecersiz_loan_type_400(self, auth_headers):
        resp = httpx.post(
            f"{API_URL}/api/sync",
            json={"tenant_id": "BANK001", "loan_type": "INVALID"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 400

    def test_eksik_tenant_422(self, auth_headers):
        resp = httpx.post(
            f"{API_URL}/api/sync",
            json={"loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

class TestE2EData:

    def test_veri_sayfalı_gelir(self, auth_headers, synced_bank):
        resp = httpx.get(
            f"{API_URL}/api/data",
            params={"tenant_id": synced_bank, "loan_type": "RETAIL", "page": 1, "page_size": 10},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert len(data["data"]) <= 10
        assert data["page"] == 1

    def test_sayfa_buyuklugu_siniri(self, auth_headers, synced_bank):
        """page_size > 1000 FastAPI validasyonu tarafından reddedilmeli (le=1000 kısıtı)."""
        resp = httpx.get(
            f"{API_URL}/api/data",
            params={"tenant_id": synced_bank, "loan_type": "RETAIL", "page_size": 9999},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 422

    def test_olmayan_tenant_bos_veri(self, auth_headers):
        resp = httpx.get(
            f"{API_URL}/api/data",
            params={"tenant_id": "GECERSIZ_BANK", "loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

class TestE2EProfiling:

    def test_profiling_temel_alanlar(self, auth_headers, synced_bank):
        resp = httpx.get(
            f"{API_URL}/api/profiling",
            params={"tenant_id": synced_bank, "loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["toplam_kayit"] > 0
        assert "faiz_istatistikleri" in data
        assert "tutar_istatistikleri" in data
        assert "veri_kalitesi" in data
        assert "durum_dagilimi" in data

    def test_profiling_null_oranlar_kapsamli(self, auth_headers, synced_bank):
        """
        null_oranlar tüm nullable/blank model alanlarını kapsamalı.
        Bu test fix #5'i doğrular.
        """
        resp = httpx.get(
            f"{API_URL}/api/profiling",
            params={"tenant_id": synced_bank, "loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 200
        null_oranlar = resp.json().get("null_oranlar", {})

        beklenen = [
            "first_payment_date", "loan_closing_date", "default_probability",
            "insurance_included", "internal_rating", "external_rating",
            "customer_district_code", "customer_province_code",
            "loan_product_type", "loan_status_flag", "customer_region_code",
            "sector_code", "internal_credit_rating", "risk_class", "customer_segment",
        ]
        eksik = [a for a in beklenen if a not in null_oranlar]
        assert not eksik, f"null_oranlar'da eksik alanlar: {eksik}"

        # Her girdide bos_sayi ve bos_pct olmalı
        for alan, deger in null_oranlar.items():
            assert "bos_sayi" in deger, f"{alan}: bos_sayi eksik"
            assert "bos_pct" in deger, f"{alan}: bos_pct eksik"

    def test_olmayan_tenant_404(self, auth_headers):
        resp = httpx.get(
            f"{API_URL}/api/profiling",
            params={"tenant_id": "GECERSIZ_BANK", "loan_type": "RETAIL"},
            headers=auth_headers,
            timeout=_TIMEOUT,
        )
        assert resp.status_code == 404
