from django.conf import settings
from django.db.models import Count, Avg, Min, Max, Sum, StdDev, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import CreditRecord, SyncLog
from .serializers import CreditRecordSerializer
from .services.sync_service import sync_credit_data


def _require_internal_token(request):
    """Dahili endpoint'ler için paylaşılan token doğrulaması."""
    token = request.headers.get("X-Internal-Token", "")
    if token != settings.INTERNAL_API_TOKEN:
        return Response(
            {"error": "Dahili API token eksik veya geçersiz"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    return None


@api_view(["POST"])
def sync_view(request):
    """
    POST /internal/sync/
    Body: {"bank_code": "BANK001", "loan_type": "RETAIL"}
    """
    err = _require_internal_token(request)
    if err:
        return err

    bank_code = request.data.get("bank_code", "").strip()
    loan_type = request.data.get("loan_type", "RETAIL").strip().upper()

    if not bank_code:
        return Response({"error": "bank_code zorunludur"}, status=status.HTTP_400_BAD_REQUEST)

    if loan_type not in ("RETAIL", "COMMERCIAL"):
        return Response(
            {"error": "loan_type RETAIL veya COMMERCIAL olmalıdır"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sonuc = sync_credit_data(bank_code, loan_type)
        return Response(sonuc, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def data_view(request):
    """
    GET /internal/data/?tenant_id=BANK001&loan_type=RETAIL&page=1&page_size=100
    Normalize edilmiş kredi kayıtlarını sayfalı döndürür.
    """
    err = _require_internal_token(request)
    if err:
        return err

    tenant_id = request.query_params.get("tenant_id", "").strip()
    loan_type = request.query_params.get("loan_type", "RETAIL").strip().upper()

    try:
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(max(1, int(request.query_params.get("page_size", 100))), 1000)
    except ValueError:
        return Response({"error": "page ve page_size tam sayı olmalıdır"}, status=400)

    if not tenant_id:
        return Response({"error": "tenant_id zorunludur"}, status=400)

    qs = (
        CreditRecord.objects.filter(
            tenant__bank_code=tenant_id,
            loan_type=loan_type,
        )
        .select_related("tenant")
        .order_by("loan_account_number")
    )

    total = qs.count()
    start = (page - 1) * page_size
    kayitlar = qs[start : start + page_size]

    return Response(
        {
            "tenant_id": tenant_id,
            "loan_type": loan_type,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
            "data": CreditRecordSerializer(kayitlar, many=True).data,
        }
    )


@api_view(["GET"])
def profiling_view(request):
    """
    GET /internal/profiling/?tenant_id=BANK001&loan_type=RETAIL
    Veri kalitesi ve dağılım istatistiklerini döndürür.
    """
    err = _require_internal_token(request)
    if err:
        return err

    tenant_id = request.query_params.get("tenant_id", "").strip()
    loan_type = request.query_params.get("loan_type", "RETAIL").strip().upper()

    if not tenant_id:
        return Response({"error": "tenant_id zorunludur"}, status=400)

    qs = CreditRecord.objects.filter(
        tenant__bank_code=tenant_id,
        loan_type=loan_type,
    )
    total = qs.count()

    if total == 0:
        return Response(
            {"error": f"{tenant_id} / {loan_type} için kayıt bulunamadı"},
            status=status.HTTP_404_NOT_FOUND,
        )

    sayisal = qs.aggregate(
        faiz_min=Min("nominal_interest_rate"),
        faiz_max=Max("nominal_interest_rate"),
        faiz_ort=Avg("nominal_interest_rate"),
        faiz_stddev=StdDev("nominal_interest_rate"),
        tutar_min=Min("original_loan_amount"),
        tutar_max=Max("original_loan_amount"),
        tutar_toplam=Sum("original_loan_amount"),
        bakiye_toplam=Sum("outstanding_principal_balance"),
    )

    bos_sigorta = qs.filter(Q(insurance_included="") | Q(insurance_included__isnull=True)).count()
    bos_dis_rating = qs.filter(Q(external_rating="") | Q(external_rating__isnull=True)).count()
    bos_ic_rating = qs.filter(Q(internal_rating="") | Q(internal_rating__isnull=True)).count()

    durum_dagilim = list(qs.values("loan_status_code").annotate(sayi=Count("id")).order_by("-sayi"))
    if loan_type == "RETAIL":
        sigorta_dagilim = list(
            qs.values("insurance_included").annotate(sayi=Count("id")).order_by("-sayi")
        )
    else:
        sigorta_dagilim = []

    son_sync = (
        SyncLog.objects.filter(tenant__bank_code=tenant_id, loan_type=loan_type, status="SUCCESS")
        .order_by("-sync_started_at")
        .first()
    )

    return Response(
        {
            "tenant_id": tenant_id,
            "loan_type": loan_type,
            "toplam_kayit": total,
            "faiz_istatistikleri": {
                "min": sayisal["faiz_min"],
                "max": sayisal["faiz_max"],
                "ortalama": round(float(sayisal["faiz_ort"] or 0), 4),
                "stddev": round(float(sayisal["faiz_stddev"] or 0), 4),
            },
            "tutar_istatistikleri": {
                "min": sayisal["tutar_min"],
                "max": sayisal["tutar_max"],
                "toplam_kullandirilan": sayisal["tutar_toplam"],
                "toplam_kalan_bakiye": sayisal["bakiye_toplam"],
            },
            "veri_kalitesi": {
                "bos_sigorta_alani": bos_sigorta,
                "bos_dis_rating": bos_dis_rating,
                "bos_ic_rating": bos_ic_rating,
                "bos_sigorta_oran_pct": round(bos_sigorta / total * 100, 2),
                "bos_dis_rating_pct": round(bos_dis_rating / total * 100, 2),
            },
            "durum_dagilimi": durum_dagilim,
            "sigorta_dagilimi": sigorta_dagilim,
            "son_senkronizasyon": (
                {
                    "tarih": son_sync.sync_started_at,
                    "bitis": son_sync.sync_finished_at,
                    "rows_fetched": son_sync.rows_fetched,
                    "rows_valid": son_sync.rows_valid,
                    "rows_invalid": son_sync.rows_invalid,
                }
                if son_sync
                else None
            ),
        }
    )
