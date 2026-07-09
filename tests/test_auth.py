"""
FastAPI auth endpoint testleri.
JWT token alma, geçersiz giriş ve korumalı endpoint'ler test edilir.
"""

import pytest
from fastapi.testclient import TestClient

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from main import app

client = TestClient(app)


class TestAuthToken:

    def test_gecerli_giris_token_doner(self):
        resp = client.post(
            "/auth/token",
            data={"username": "admin", "password": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_yanlis_sifre_401(self):
        resp = client.post(
            "/auth/token",
            data={"username": "admin", "password": "yanlis_sifre"},
        )
        assert resp.status_code == 401

    def test_olmayan_kullanici_401(self):
        resp = client.post(
            "/auth/token",
            data={"username": "hacker", "password": "admin"},
        )
        assert resp.status_code == 401

    def test_readonly_kullanici_giris(self):
        resp = client.post(
            "/auth/token",
            data={"username": "readonly", "password": "readonly"},
        )
        assert resp.status_code == 200


class TestKorumaEndpointleri:

    def _token_al(self, username="admin", password="admin"):
        resp = client.post(
            "/auth/token",
            data={"username": username, "password": password},
        )
        return resp.json()["access_token"]

    def test_token_olmadan_data_401(self):
        resp = client.get("/api/data?tenant_id=BANK001")
        assert resp.status_code == 401

    def test_token_olmadan_sync_401(self):
        resp = client.post("/api/sync?tenant_id=BANK001")
        assert resp.status_code == 401

    def test_token_olmadan_profiling_401(self):
        resp = client.get("/api/profiling?tenant_id=BANK001")
        assert resp.status_code == 401

    def test_gecersiz_token_401(self):
        resp = client.get(
            "/api/data?tenant_id=BANK001",
            headers={"Authorization": "Bearer bu_token_gecersiz"},
        )
        assert resp.status_code == 401

    def test_health_token_gerektirmez(self):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_gecerli_token_ile_istek(self):
        """Geçerli token ile istek atıldığında 401 DEĞİL başka bir hata gelmeli.
        (Adapter çalışmıyorsa 503, ama 401 olmaz.)"""
        token = self._token_al()
        resp = client.get(
            "/api/data?tenant_id=BANK001&loan_type=RETAIL",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code != 401

    def test_jwt_payload_kullanici_adi(self):
        """Token payload'ında sub (username) doğru olmalı."""
        import base64, json

        token = self._token_al()
        payload_b64 = token.split(".")[1]

        padding = 4 - len(payload_b64) % 4
        payload_b64 += "=" * padding
        payload = json.loads(base64.b64decode(payload_b64))
        assert payload["sub"] == "admin"
