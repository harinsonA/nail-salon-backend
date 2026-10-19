from django.conf import settings
from django.core.checks import Error


def check_lock_settings(app_configs, **kwargs):
    errors = []
    temporary = settings.SECURITY_TEMPORARY_LOCK_FAILURES
    permanent = settings.SECURITY_PERMANENT_LOCK_FAILURES
    if temporary < 1 or temporary >= permanent:
        errors.append(
            Error(
                "SECURITY_TEMPORARY_LOCK_FAILURES debe ser al menos 1 y menor que SECURITY_PERMANENT_LOCK_FAILURES.",
                hint=f"Hoy valen {temporary} y {permanent}.",
                id="seguridad.E001",
            )
        )
    if settings.SECURITY_TEMPORARY_LOCK_MINUTES < 1:
        errors.append(
            Error(
                "SECURITY_TEMPORARY_LOCK_MINUTES debe ser al menos 1.",
                hint=f"Hoy vale {settings.SECURITY_TEMPORARY_LOCK_MINUTES}.",
                id="seguridad.E002",
            )
        )
    return errors
