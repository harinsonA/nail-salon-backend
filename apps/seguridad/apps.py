from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.checks import register


class SeguridadConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.seguridad"
    label = "seguridad"
    verbose_name = "Seguridad"

    def ready(self):
        from apps.seguridad.checks import check_lock_settings
        from apps.seguridad.signals import end_session_on_logout, reset_failures_on_login, start_session_on_login

        register(check_lock_settings)
        user_logged_in.connect(reset_failures_on_login, dispatch_uid="seguridad_reset_failures_on_login")
        user_logged_in.connect(start_session_on_login, dispatch_uid="seguridad_start_session_on_login")
        user_logged_out.connect(end_session_on_logout, dispatch_uid="seguridad_end_session_on_logout")
