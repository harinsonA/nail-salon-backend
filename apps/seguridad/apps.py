from django.apps import AppConfig
from django.core.checks import register


class SeguridadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.seguridad"
    label = "seguridad"
    verbose_name = "Seguridad"

    def ready(self):
        from apps.seguridad.checks import check_lock_settings

        register(check_lock_settings)
