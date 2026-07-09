# TeamSec — Finansal Veri Entegrasyon Adaptörü

Harici banka API'sinden CSV formatındaki kredi portföy verilerini çeken, doğrulayan, normalize eden ve bir veri ambarında saklayan çok servisli entegrasyon sistemi.

---

## Mimari

```
[Tarayıcı / İstemci]
        ↓  JWT veya X-API-Key
[FastAPI api/ :8000]          ← /api/sync  /api/data  /api/profiling
        ↓  HTTP
[Django adapter/ :8002]       ← ORM, sync mantığı, normalizasyon
   ↓              ↓
[PostgreSQL]   [Rust Engine]  ← PyO3 köprüsü ile validation
                    ↑
[FastAPI external_bank/ :8001] ← Banka simülatörü (CSV → JSON)
```

**Teknoloji Yığını:** Django 4.2 · FastAPI · Rust + PyO3 · React + Vite · PostgreSQL · Docker

---

## Hızlı Başlangıç (Docker)

```bash
# 1. Repo klonla
git clone https://github.com/alabora33/Financial-Data-Integration-Adapter.git
cd Financial-Data-Integration-Adapter

# 2. Ortam değişkenlerini hazırla
cp .env.example .env

# 3. Tüm servisleri başlat (ilk build ~5 dakika — Rust derleme dahil)
sudo docker compose up --build -d

# 4. Örnek veriyi yükle
sudo docker compose exec adapter python manage.py seed_bank

# 5. Tarayıcıdan eriş
#   Frontend  → http://localhost:5173  (admin / admin)
#   Swagger   → http://localhost:8000/docs
#   Admin     → http://localhost:8002/admin
```

---

## Servisler

| Servis | URL | Açıklama |
|---|---|---|
| Frontend (React) | `localhost:5173` | Senkronizasyon, veri görüntüleme, profiling |
| Public API (FastAPI) | `localhost:8000` | `/api/sync` `/api/data` `/api/profiling` |
| Swagger UI | `localhost:8000/docs` | İnteraktif API dokümantasyonu |
| Django Adapter | `localhost:8002` | İç servis, ORM, senkronizasyon |
| Django Admin | `localhost:8002/admin` | Veri ambarı yönetim paneli |
| Banka Simülatörü | `localhost:8001` | Harici banka taklidi |

---

## Kimlik Doğrulama

**Yöntem 1 — JWT Bearer:**
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=admin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/profiling?tenant_id=BANK001&loan_type=RETAIL"
```

**Yöntem 2 — API Key:**
```bash
curl -H "X-API-Key: teamsec-dev-key" \
  "http://localhost:8000/api/data?tenant_id=BANK001&loan_type=RETAIL"
```

API key'ler `.env` dosyasındaki `API_KEYS` değişkeni ile yönetilir.

**Yöntem 3 — Kullanıcı Kaydı:**
```bash
# Yeni hesap oluştur
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "yenikullanici", "password": "gizlisifre"}'

# Kayıtlı hesapla giriş yap
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -d "username=yenikullanici&password=gizlisifre" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Kayıtlı kullanıcılar **reader** rolüyle tüm tenant'ları görüntleyebilir; sync başlatma ve upload yalnızca **admin** rolündedir.
Kayıtlar `api/users.json` dosyasında bcrypt hash'li olarak saklanır.

---

## API Endpoint'leri

### `POST /api/sync`
Bankadan veri çeker, doğrular, normalize eder, veri ambarına kaydeder.
```
?tenant_id=BANK001&loan_type=RETAIL
Authorization: Bearer <token>
```

### `GET /api/data`
Normalize edilmiş kredi kayıtlarını sayfalı döndürür.
```
?tenant_id=BANK001&loan_type=RETAIL&page=1&page_size=100
```

### `GET /api/profiling`
Veri kalitesi raporu: faiz/tutar istatistikleri, boş alan oranları, kategorik dağılımlar.
```
?tenant_id=BANK001&loan_type=RETAIL
```

### `POST /api/upload`
CSV dosyasını banka simülatörüne yükler (frontend → API → external_bank). JWT token gerektirir.
```
?tenant_id=BANK001&loan_type=RETAIL&data_kind=credit
Content-Type: multipart/form-data
Authorization: Bearer <token>
```
Yükleme mevcut veriyi değiştirir (replace). `data_kind`: `credit` veya `payment_plan`.

---

## Multi-Tenant Tasarım

### İzolasyon Katmanları

| Katman | Mekanizma |
|---|---|
| **Veri izolasyonu** | Her `CreditRecord` / `PaymentPlan` bir `Tenant` FK'ya bağlı; sorgular her zaman `tenant__bank_code=X` filtresiyle çalışır |
| **JWT izolasyonu** | `allowed_tenants` alanı; `bank001user` kullanıcısı yalnızca `BANK001` verisine erişebilir |
| **API Key izolasyonu** | `API_KEYS=key:role:BANK001\|BANK002` formatı; belirtilmezse `*` (tam erişim) |
| **Dahili servis** | `api/ → adapter/` arası `X-Internal-Token` ile korunur; dışarıya açık değil |

### Tasarım Kararları

- **Tek DB, çok tenant:** Tenant başına ayrı DB yerine tablo bazlı izolasyon tercih edildi — küçük-orta ölçekte yeterli, yönetimi basit.
- **API Key tenant kısıtı:** `API_KEYS` env değişkeninde `key:role:TENANT1|TENANT2` formatıyla atanır. Tenant belirtilmeyen key'ler varsayılan olarak `*` (tüm bankalar) erişimine sahiptir.
- **Cross-tenant sızıntı önlemi:** Tüm `/internal/*` endpoint'lerinde `tenant_id` sorgu parametresi zorunludur; eksik parametre `400` döner.

---

## Validation Davranışı

| Senaryo | Sonuç |
|---|---|
| Tüm kredi satırları geçersiz | Eski veri **korunur**, sync yazma adımı atlanır |
| Tüm ödeme planı satırları geçersiz | Eski ödeme planları **korunur**, silme adımı atlanır |
| Kısmen geçersiz batch | **Geçerli satırlar yazılır**, geçersiz satırlar atlanır ve hata sayısı raporlanır |

Bu tasarım karar olarak seçilmiştir: kısmen geçerli veri tamamen bloklamak yerine en iyi çabayı uygular.

---

## Multi-Tenant Kullanımı

Sistem BANK001/002/003 gibi birden fazla bankayı izole eder. Yeni banka verisi eklemek için:

```bash
# CSV dosyasını {TENANT}__{LOAN_TYPE}__{DATA_KIND}.csv formatında koy
# Örnek: BANK002__RETAIL__credit.csv
sudo docker compose exec adapter python manage.py seed_bank \
  --file /sample_data/BANK002__RETAIL__credit.csv
```

**Demo: Masked CSV'leri farklı tenant'lara yükle**

Repo’daki örnek veriler `retail_credit_masked.csv` gibi isimlendirilmiştir.
`--tenant-id` ile hangi bankaya yükleneceğini belirtebilirsiniz:

```bash
# BANK001 (varsayılan)
sudo docker compose exec adapter python manage.py seed_bank

# BANK002 için aynı CSV'ler
sudo docker compose exec adapter python manage.py seed_bank --tenant-id BANK002

# BANK003 için
sudo docker compose exec adapter python manage.py seed_bank --tenant-id BANK003
```

---

## Validation Kuralları

| Tür | Kontrol |
|---|---|
| **Alan varlığı** | Zorunlu alanlar boş olamaz |
| **Sayı + aralık** | `nominal_interest_rate`: 0–1000 arası |
| **Tarih formatı** | YYYYMMDD veya YYYY-MM-DD, takvimce gerçek tarih |
| **Enum** | `insurance_included`: E/H, `installment_status`: A/K |
| **Cross-file** | Her ödeme planı satırının `loan_account_number`'ı kredi tablosunda olmalı |

Validation motoru Rust ile yazılmış (`rust_engine/`), PyO3 köprüsüyle Python'dan çağrılır.

---

## Normalizasyon

| Alan | Ham Değer → Standart |
|---|---|
| Tarih | `20250302` veya `2025-03-02` → `date(2025,3,2)` |
| Faiz/Tutar | `"55,47"` veya `"55.47"` → `Decimal("55.47")` |
| `customer_type` | `I`, `Individual` → `BIREYSEL` |
| `customer_type` | `C`, `Corporate` → `KURUMSAL` |
| `loan_status_code` | `A`, `Active` → `AKTIF` |
| `installment_status` | `K`, `Closed`, `Paid` → `KAPALI` |

---

## Testleri Çalıştır

```bash
# Python testleri (125 test, SQLite in-memory)
cd adapter && source .venv/bin/activate && cd ..
python -m pytest tests/ -v

# Rust birim testleri (15 test)
cd rust_engine && cargo test
```

---

## Bellek Verimliliği

269K+ satırlık ödeme planı verisini işlerken bellekte hiçbir zaman `CHUNK_SIZE` (varsayılan: 5000) satırdan fazla tutulmaz. `SYNC_CHUNK_SIZE` ortam değişkeni ile ayarlanabilir.

**200 MB dosya benchmark:** `SYNC_CHUNK_SIZE=5000` ile ~270K satır (≈220 MB CSV) senkronizasyonu sırasında adapter RAM kullanımı ölçülen maksimum ~45 MB ile sınırlı kaldı. Bu değer `docker stats` ile doğrulanabilir:
```bash
docker stats teamsec-adapter-adapter-1 --no-stream
```

