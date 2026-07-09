"""
python manage.py seed_bank

Kullanım biçimleri:

1) Varsayılan — /sample_data/teamsec-interview-data içindeki
   {TENANT}__{LOAN_TYPE}__{DATA_KIND}.csv formatındaki TÜM dosyaları yükle:
       python manage.py seed_bank

2) Belirli bir dizini tara:
       python manage.py seed_bank --dir /baska/klasor

3) Tek dosya yükle:
       python manage.py seed_bank --file /yol/BANK002__COMMERCIAL__credit.csv

4) Yalnızca ilk N satırı yükle (büyük dosyalar için test):
       python manage.py seed_bank --limit 1000
"""

import os
import re
import requests
from django.core.management.base import BaseCommand, CommandError

BANK_URL = os.environ.get("BANK_BASE_URL", "http://external_bank:8001")
DEFAULT_DIR = "/sample_data/teamsec-interview-data"

PATTERN = re.compile(r"^([^_]+)__([^_]+)__([^_]+)\.csv$", re.IGNORECASE)

BILINEN_DOSYALAR: dict[str, tuple[str, str]] = {
    "retail_credit_masked.csv": ("RETAIL", "credit"),
    "retail_payment_plan_masked.csv": ("RETAIL", "payment_plan"),
    "commercial_credit_masked.csv": ("COMMERCIAL", "credit"),
    "commercial_payment_plan_masked.csv": ("COMMERCIAL", "payment_plan"),
}


def _parse_filename(dosya_adi: str):
    """
    'BANK001__RETAIL__credit.csv' → ('BANK001', 'RETAIL', 'credit')
    Eşleşmezse None döner.
    """
    m = PATTERN.match(os.path.basename(dosya_adi))
    if not m:
        return None
    return m.group(1), m.group(2).upper(), m.group(3).lower()


def _upload(bank_url, yol, tenant_id, loan_type, data_kind, limit, stdout, style):
    """Tek bir CSV dosyasını external_bank'a yükler."""
    if not os.path.exists(yol):
        stdout.write(style.WARNING(f"  ATLANDI: {yol} bulunamadı"))
        return

    if limit > 0:
        with open(yol, "r", encoding="utf-8") as f:
            satirlar = []
            for i, satir in enumerate(f):
                satirlar.append(satir)
                if i >= limit:
                    break
        icerik = "".join(satirlar).encode("utf-8")
    else:
        with open(yol, "rb") as f:
            icerik = f.read()

    kb = len(icerik) / 1024
    stdout.write(
        f"  Yükleniyor: {os .path .basename (yol )} ({kb :.0f} KB) → {tenant_id}/{loan_type}/{data_kind}..."
    )

    try:
        resp = requests.post(
            f"{bank_url}/upload",
            params={"tenant_id": tenant_id, "loan_type": loan_type, "data_kind": data_kind},
            files={"file": (os.path.basename(yol), icerik, "text/csv")},
            timeout=300,
        )
        resp.raise_for_status()
        sonuc = resp.json()
        stdout.write(style.SUCCESS(f"  ✓ {sonuc ['row_count']:,} satır yüklendi"))
    except Exception as e:
        stdout.write(style.ERROR(f"  ✗ Hata: {e}"))


class Command(BaseCommand):
    help = (
        "CSV dosyalarını external_bank simülatörüne yükler. "
        "Dosya adı formatı: {TENANT}__{LOAN_TYPE}__{DATA_KIND}.csv"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=DEFAULT_DIR,
            help=f"Taranacak dizin (varsayılan: {DEFAULT_DIR})",
        )
        parser.add_argument(
            "--file",
            default=None,
            help="Tek dosya yükle: /yol/BANK002__RETAIL__credit.csv",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Her dosyadan maks satır sayısı (0 = tümü)",
        )
        parser.add_argument(
            "--tenant-id",
            default=None,
            dest="tenant_id",
            help="Dosya adındaki tenant'ı geçersiz kıl (örn: BANK002)",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        tek_dosya = options["file"]
        tenant_override = options["tenant_id"]

        self.stdout.write(self.style.HTTP_INFO("=== external_bank seed başlıyor ===\n"))
        if tenant_override:
            self.stdout.write(f"  → Tenant override: {tenant_override}\n")

        if tek_dosya:

            parsed = _parse_filename(tek_dosya)
            if not parsed:
                raise CommandError(
                    f"Dosya adı formatı hatalı: '{os .path .basename (tek_dosya )}'\n"
                    f"Beklenen: {{TENANT}}_{{LOAN_TYPE}}_{{DATA_KIND}}.csv"
                )
            tenant_id, loan_type, data_kind = parsed
            if tenant_override:
                tenant_id = tenant_override
            _upload(
                BANK_URL, tek_dosya, tenant_id, loan_type, data_kind, limit, self.stdout, self.style
            )
        else:

            dizin = options["dir"]
            if not os.path.isdir(dizin):
                raise CommandError(f"Dizin bulunamadı: {dizin}")

            bulunan = sorted(f for f in os.listdir(dizin) if f.endswith(".csv"))
            if not bulunan:
                self.stdout.write(self.style.WARNING(f"  {dizin} içinde CSV bulunamadı."))
                return

            for dosya_adi in bulunan:
                parsed = _parse_filename(dosya_adi)

                if not parsed:

                    bilinen = BILINEN_DOSYALAR.get(dosya_adi)
                    if bilinen:
                        loan_type, data_kind = bilinen

                        tenant_id = tenant_override if tenant_override else "BANK001"
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ATLANDI '{dosya_adi}' — format uyumsuz "
                                f"(BILINEN_DOSYALAR listesine ekleyin veya --tenant-id kullanın)"
                            )
                        )
                        continue
                else:
                    tenant_id, loan_type, data_kind = parsed
                    if tenant_override:
                        tenant_id = tenant_override
                yol = os.path.join(dizin, dosya_adi)
                _upload(
                    BANK_URL, yol, tenant_id, loan_type, data_kind, limit, self.stdout, self.style
                )

        self.stdout.write(self.style.SUCCESS("\n=== Seed tamamlandı ==="))
