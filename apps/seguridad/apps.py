from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in
from django.core.checks import register


class SeguridadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.seguridad"
    label = "seguridad"
    verbose_name = "Seguridad"

    def ready(self):
        from apps.seguridad.checks import check_lock_settings
        from apps.seguridad.signals import reset_failures_on_login

        register(check_lock_settings)
        user_logged_in.connect(reset_failures_on_login, dispatch_uid="seguridad_reset_failures_on_login")
