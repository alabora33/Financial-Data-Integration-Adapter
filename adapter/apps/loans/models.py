from django.db import models


class Tenant(models.Model):
    """
    Kiracı — sisteme bağlı her banka bir Tenant'tır.
    Örnek: BANK001, BANK002, BANK003
    """
    bank_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tenant"

    def __str__(self):
        return self.bank_code


class CreditRecord(models.Model):
    """
    Kredi kaydı — retail ve commercial verisi tek tabloda,
    loan_type alanıyla ayrılır. Commercial'a özgü alanlar null olabilir.
    """

    LOAN_TYPE_CHOICES = [
        ("RETAIL", "Bireysel"),
        ("COMMERCIAL", "Ticari"),
    ]

    # --- Kimlik ---
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="credits")
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES)
    loan_account_number = models.CharField(max_length=50)
    customer_id = models.CharField(max_length=50)
    customer_type = models.CharField(max_length=5)          # I=Bireysel, C=Kurumsal

    # --- Kredi durumu ---
    loan_status_code = models.CharField(max_length=10)
    days_past_due = models.IntegerField(default=0)

    # --- Tarihler ---
    loan_start_date = models.DateField()
    final_maturity_date = models.DateField()
    first_payment_date = models.DateField(null=True, blank=True)
    loan_closing_date = models.DateField(null=True, blank=True)

    # --- Taksit sayıları ---
    total_installment_count = models.IntegerField(default=0)
    outstanding_installment_count = models.IntegerField(default=0)
    paid_installment_count = models.IntegerField(default=0)
    grace_period_months = models.IntegerField(default=0)
    installment_frequency = models.IntegerField(default=1)

    # --- Tutarlar (DecimalField: para/faiz için zorunlu, float değil) ---
    original_loan_amount = models.DecimalField(max_digits=18, decimal_places=2)
    outstanding_principal_balance = models.DecimalField(max_digits=18, decimal_places=2)
    total_interest_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # --- Faiz ve vergi oranları ---
    nominal_interest_rate = models.DecimalField(max_digits=10, decimal_places=4)
    kkdf_rate = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    kkdf_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bsmv_rate = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    bsmv_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # --- Rating ---
    internal_rating = models.CharField(max_length=20, blank=True)
    external_rating = models.CharField(max_length=20, blank=True)

    # --- Sadece RETAIL ---
    customer_district_code = models.CharField(max_length=20, blank=True)
    customer_province_code = models.CharField(max_length=20, blank=True)
    insurance_included = models.CharField(max_length=1, blank=True)  # E / H

    # --- Sadece COMMERCIAL ---
    loan_product_type = models.CharField(max_length=50, blank=True)
    loan_status_flag = models.CharField(max_length=10, blank=True)
    customer_region_code = models.CharField(max_length=20, blank=True)
    sector_code = models.CharField(max_length=20, blank=True)
    internal_credit_rating = models.CharField(max_length=20, blank=True)
    default_probability = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    risk_class = models.CharField(max_length=20, blank=True)
    customer_segment = models.CharField(max_length=50, blank=True)

    # --- Meta ---
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "credit_record"
        # Aynı tenant + kredi tipi + hesap no kombinasyonu tekrar edemez
        unique_together = ("tenant", "loan_type", "loan_account_number")
        indexes = [
            models.Index(fields=["tenant", "loan_type"]),
            models.Index(fields=["loan_account_number"]),
        ]

    def __str__(self):
        return f"{self.loan_account_number} ({self.loan_type})"


class PaymentPlan(models.Model):
    """
    Ödeme planı taksitleri — her CreditRecord'a ait satırlar.
    """
    credit = models.ForeignKey(
        CreditRecord, on_delete=models.CASCADE, related_name="payment_plans"
    )
    installment_number = models.IntegerField()
    scheduled_payment_date = models.DateField()
    actual_payment_date = models.DateField(null=True, blank=True)

    installment_amount = models.DecimalField(max_digits=18, decimal_places=2)
    principal_component = models.DecimalField(max_digits=18, decimal_places=2)
    interest_component = models.DecimalField(max_digits=18, decimal_places=2)
    kkdf_component = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    bsmv_component = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    installment_status = models.CharField(max_length=5)    # A=Açık, K=Kapalı

    remaining_principal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    remaining_interest = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    remaining_kkdf = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    remaining_bsmv = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "payment_plan"
        unique_together = ("credit", "installment_number")

    def __str__(self):
        return f"{self.credit.loan_account_number} — Taksit {self.installment_number}"


class SyncLog(models.Model):
    """
    Senkronizasyon geçmişi — her çekme işlemi bir SyncLog kaydı oluşturur.
    """

    STATUS_CHOICES = [
        ("PENDING", "Devam Ediyor"),
        ("SUCCESS", "Başarılı"),
        ("FAILED", "Başarısız"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="sync_logs")
    loan_type = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    sync_started_at = models.DateTimeField(auto_now_add=True)
    sync_finished_at = models.DateTimeField(null=True, blank=True)

    rows_fetched = models.IntegerField(default=0)
    rows_valid = models.IntegerField(default=0)
    rows_invalid = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "sync_log"
        ordering = ["-sync_started_at"]

    def __str__(self):
        return f"{self.tenant} / {self.loan_type} / {self.status}"
