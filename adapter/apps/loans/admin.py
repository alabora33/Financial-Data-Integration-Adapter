from django.contrib import admin
from .models import Tenant, CreditRecord, PaymentPlan, SyncLog


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("bank_code", "name", "created_at")


@admin.register(CreditRecord)
class CreditRecordAdmin(admin.ModelAdmin):
    list_display = ("loan_account_number", "loan_type", "tenant", "loan_status_code", "synced_at")
    list_filter = ("loan_type", "tenant", "loan_status_code")
    search_fields = ("loan_account_number", "customer_id")


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ("credit", "installment_number", "scheduled_payment_date", "installment_status")
    list_filter = ("installment_status",)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ("tenant", "loan_type", "status", "rows_fetched", "rows_valid", "rows_invalid", "sync_started_at")
    list_filter = ("status", "loan_type", "tenant")
