from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .services.sync_service import sync_credit_data


@api_view(["POST"])
def sync_view(request):
    """
    POST /internal/sync/
    Body: {"bank_code": "BANK001", "loan_type": "RETAIL"}
    """
    bank_code = request.data.get("bank_code", "").strip()
    loan_type = request.data.get("loan_type", "RETAIL").strip().upper()

    if not bank_code:
        return Response(
            {"error": "bank_code zorunludur"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if loan_type not in ("RETAIL", "COMMERCIAL"):
        return Response(
            {"error": "loan_type RETAIL veya COMMERCIAL olmalıdır"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        sonuc = sync_credit_data(bank_code, loan_type)
        return Response(sonuc, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
