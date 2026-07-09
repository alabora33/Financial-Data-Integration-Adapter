# Sistem Mimarisi

## Genel Bakış

TeamSec Adapter, çoklu bankadan gelen finansal kredi verilerini normalize eden, doğrulayan ve tek bir API üzerinden sunan bir entegrasyon adaptörüdür.

```
┌─────────────────────────────────────────────────────────────────┐
│                        İstemci Katmanı                          │
│  Frontend (React/Vite :5173)                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/JSON (JWT veya API Key)
┌──────────────────────────▼──────────────────────────────────────┐
│                    Public API Katmanı                           │
│  FastAPI  (:8000)                                               │
│  • JWT / API Key kimlik doğrulama                               │
│  • Tenant izolasyon kontrolü                                    │
│  • Route: /auth/token  /api/sync  /api/data  /api/profiling     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/JSON + X-Internal-Token
┌──────────────────────────▼──────────────────────────────────────┐
│                    Adapter Katmanı                              │
│  Django + DRF  (:8002)                                          │
│  • İş mantığı: normalizasyon, doğrulama, senkronizasyon        │
│  • APScheduler: periyodik sync (SYNC_INTERVAL_MINUTES)          │
│  • Route: /internal/sync  /internal/data  /internal/profiling   │
└──────┬─────────────────────────────────────┬────────────────────┘
       │ Django ORM                          │ HTTP (requests)
┌──────▼──────────┐               ┌──────────▼──────────────────┐
│  PostgreSQL     │               │  Harici Banka Simülatörü    │
│  (:5432)        │               │  FastAPI  (:8001)           │
│  • CreditRecord │               │  • /upload  /data  /health  │
│  • PaymentPlan  │               │  • Per-tenant CSV depolama  │
│  • Tenant       │               └─────────────────────────────┘
│  • SyncLog      │
└─────────────────┘
```

---

## Servisler

| Servis | Teknoloji | Port | Sorumluluk |
|---|---|---|---|
| `external_bank` | FastAPI | 8001 | Banka simülatörü: CSV yükleme, sayfalı veri servisi |
| `adapter` | Django 4.2 + DRF | 8002 | Normalizasyon, doğrulama, senkronizasyon, periyodik sync |
| `api` | FastAPI | 8000 | Public API: kimlik doğrulama, tenant izolasyonu, yönlendirme |
| `frontend` | React + Vite | 5173 | Kullanıcı arayüzü: sync, veri tablosu, profiling |
| `db` | PostgreSQL 15 | 5432 | Kalıcı depolama |

---

## Multi-Tenant Tasarım Kararı

### Seçilen Yaklaşım: Tek Şema, FK Tabanlı İzolasyon

Her tablo `tenant (FK → Tenant)` sütunu içerir. Tüm sorgular bu FK üzerinden filtrelenir.

**Neden bu yaklaşım?**

- **Basitlik**: Ayrı şema veya veritabanı yönetimi gerektirmez; Django ORM ile doğrudan desteklenir.
- **Ölçeklenebilirlik**: Tenant sayısı arttıkça yeni tablo veya migration gerekmez.
- **Atomik güncelleme**: Tek `transaction.atomic()` ile bir tenant'ın tüm kredi verileri güvenle değiştirilebilir.
- **Veri izolasyonu**: `unique_together = [("tenant", "loan_account_number")]` kısıtı ile farklı tenant'ların aynı hesap numarasına sahip kayıtları çakışmaz.

**Alternatifler ve neden seçilmedi?**

| Alternatif | Dezavantaj |
|---|---|
| Ayrı PostgreSQL şeması | Django ile yönetimi karmaşık, migration'lar her tenant için ayrı çalışmalı |
| Ayrı veritabanı | Bağlantı havuzu karmaşıklığı, bakım yükü çok yüksek |
| Row-level security (RLS) | PostgreSQL RLS ile Django ORM entegrasyonu zorlu |

### Tenant İzolasyonu Katmanları

1. **DB katmanı**: Her sorgu `tenant__bank_code=...` filtresi içerir.
2. **Uygulama katmanı (adapter)**: `_sync_credits` / `_sync_payment_plans` tenant parametresi ile çalışır; cross-tenant sorgu yapısal olarak mümkün değil.
3. **API katmanı**: `_check_tenant_access()` kullanıcının `allowed_tenants` listesini kontrol eder.
4. **Güvenlik katmanı**: `/internal/` endpoint'leri `X-Internal-Token` header doğrulamasına tabidir; dış dünya bu endpoint'lere doğrudan erişemez.

---

## Veri Akışı

### Senkronizasyon Akışı

```
POST /api/sync {tenant_id, loan_type}
  → FastAPI: JWT doğrula → tenant erişim kontrolü
  → POST /internal/sync/ + X-Internal-Token header
    → Django: token doğrula
    → _fetch_all(): sayfalı (CHUNK_SIZE=5000) HTTP GET → external_bank
    → Her satır için: validate() → normalize()
    → Tüm satırlar geçersizse: ERKENden dön, eski veri korunur  ← KRİTİK İŞ KURALI
    → transaction.atomic(): eski kayıtları sil → bulk_create(geçerli)
    → _sync_payment_plans(): cross-file validation (loan_account_number eşleşmesi)
    → SyncLog kaydet
```

### Normalizasyon Hattı

```
Ham CSV satırı
  → parse_date()   : YYYYMMDD | YYYY-MM-DD | DD.MM.YYYY → Python date
  → parse_rate()   : "18.5%" | "0.185" | "1850bps" → Decimal
  → parse_decimal(): virgül → nokta dönüşümü
  → parse_category(): "K"/"Kapalı"/"Paid" → "KAPALI" (standart kod)
  → Normalize edilmiş Django model dict
```

---

## Doğrulama Stratejisi

### İki Katmanlı Doğrulama

1. **Rust (PyO3)** — RETAIL kredileri için yüksek performanslı doğrulama (`rust_validator.validate_row`).  
   Rust modülü import edilemezse Python fallback devreye girer.

2. **Python** — COMMERCIAL krediler ve ödeme planları için.

### Geçersiz Veri Koruması

Yeni bir sync batch'inde tüm satırlar geçersizse (`rows_fetched > 0` ve `len(geçerli) == 0`), veritabanındaki eski veriler **silinmez**. Bu sayede bozuk bir veri kaynağı geçmiş geçerli veriyi ezemez.

---

## Güvenlik

| Mekanizma | Açıklama |
|---|---|
| JWT Bearer | `POST /auth/token` ile alınan erişim tokenı (60 dk TTL) |
| API Key | `X-API-Key` header; ortam değişkeni `API_KEYS` ile yapılandırılır |
| X-Internal-Token | `api/` ↔ `adapter/` arası paylaşılan sır; `/internal/` endpoint'lerini korur |
| Tenant izolasyonu | Her kullanıcının `allowed_tenants` listesi; `["*"]` = tam erişim |
| CORS | Yalnızca `localhost:5173` ve `localhost:3000`'e izin verilir |

---

## Periyodik Senkronizasyon

`adapter` servisi başlarken `LoansConfig.ready()` metodu APScheduler'ı başlatır.

```
SYNC_INTERVAL_MINUTES=60    # dakika cinsinden aralık (0 = devre dışı)
SYNC_TENANTS=BANK001,BANK002,BANK003
SYNC_LOAN_TYPES=RETAIL,COMMERCIAL
```

Scheduler, her `SYNC_INTERVAL_MINUTES` dakikada bir `SYNC_TENANTS × SYNC_LOAN_TYPES` kombinasyonlarını otomatik olarak senkronize eder. Hata oluşursa loglama yapılır, diğer tenant'lar etkilenmez.

---

## Veri Modeli (Özet)

```
Tenant (bank_code PK benzeri)
  └── CreditRecord (loan_account_number, loan_type, tenant FK)
        unique_together: (tenant, loan_account_number)
        └── PaymentPlan (credit FK, installment_number)

  └── SyncLog (tenant FK, loan_type, status, rows_*)
```

---

## Bellek Verimliliği

- Harici bankadan veri `CHUNK_SIZE=5000` satırlık sayfalar halinde çekilir.  
  Tipik bellek kullanımı: `5000 satır × 30 alan × ~20 byte ≈ 3 MB/chunk`.
- Ödeme planları chunk'lar halinde işlenir ve DB'ye yazılır; tamamı hiçbir zaman RAM'de tutulmaz.
- Kredi kayıtları (maks ~25K/tenant) doğrulama için önce toplanır (~5 MB), sonra atomik olarak yazılır.
