from rest_framework import serializers
from .models import CreditRecord, SyncLog


class CreditRecordSerializer(serializers.ModelSerializer):
    tenant_bank_code = serializers.CharField(source="tenant.bank_code", read_only=True)

    class Meta:
        model = CreditRecord
        exclude = ("tenant",)  # tenant FK yerine tenant_bank_code string'i dön


class SyncLogSerializer(serializers.ModelSerializer):
    tenant_bank_code = serializers.CharField(source="tenant.bank_code", read_only=True)

    class Meta:
        model = SyncLog
        fields = "__all__"
