import os
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class LoansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.loans"
    verbose_name = "Krediler"

    def ready(self):

        if os.environ.get("RUN_MAIN") == "true" or not os.environ.get("DJANGO_SETTINGS_MODULE"):
            return
        self._start_scheduler()

    @staticmethod
    def _start_scheduler():
        sync_interval = int(os.environ.get("SYNC_INTERVAL_MINUTES", "60"))
        if sync_interval <= 0:
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
        except ImportError:
            logger.warning("APScheduler kurulu değil; periyodik sync devre dışı.")
            return

        def _periodic_sync():
            from apps.loans.services.sync_service import sync_credit_data

            tenants = os.environ.get("SYNC_TENANTS", "BANK001,BANK002,BANK003").split(",")
            loan_types = os.environ.get("SYNC_LOAN_TYPES", "RETAIL,COMMERCIAL").split(",")
            for tenant in tenants:
                for loan_type in loan_types:
                    try:
                        logger.info("Periyodik sync: %s / %s", tenant.strip(), loan_type.strip())
                        sync_credit_data(tenant.strip(), loan_type.strip())
                    except Exception as exc:
                        logger.error(
                            "Periyodik sync hatası %s/%s: %s",
                            tenant,
                            loan_type,
                            exc,
                        )

        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            _periodic_sync,
            trigger=IntervalTrigger(minutes=sync_interval),
            id="periodic_sync",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()
        logger.info("Periyodik sync scheduler başlatıldı (her %d dakikada bir).", sync_interval)
