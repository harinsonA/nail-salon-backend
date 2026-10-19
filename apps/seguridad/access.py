from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.seguridad.models import AccesoUsuario


class LockState(Enum):
    FREE = "free"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"


@dataclass(frozen=True)
class LockStatus:
    state: LockState
    until: datetime | None = None
    failures: int = 0
    last_failure: datetime | None = None

    @property
    def is_locked(self):
        return self.state is not LockState.FREE

    @property
    def remaining_attempts(self):
        if self.is_locked:
            return 0
        if self.failures < settings.SECURITY_TEMPORARY_LOCK_FAILURES:
            return settings.SECURITY_TEMPORARY_LOCK_FAILURES - self.failures
        return settings.SECURITY_PERMANENT_LOCK_FAILURES - self.failures

    @property
    def next_lock_is_permanent(self):
        return self.failures >= settings.SECURITY_TEMPORARY_LOCK_FAILURES


def status_of(access, now=None):
    if access is None:
        return LockStatus(LockState.FREE)
    now = now or timezone.now()
    details = {"failures": access.intentos_fallidos, "last_failure": access.ultimo_intento_fallido}
    if access.bloqueado:
        return LockStatus(LockState.PERMANENT, **details)
    if access.bloqueado_hasta and access.bloqueado_hasta > now:
        return LockStatus(LockState.TEMPORARY, until=access.bloqueado_hasta, **details)
    return LockStatus(LockState.FREE, **details)


def describe_lock(status):
    if status.state is LockState.PERMANENT:
        return "Bloqueado hasta que alguien lo desbloquee"
    if status.state is LockState.TEMPORARY:
        return f"Bloqueado hasta las {timezone.localtime(status.until).strftime('%H:%M')}"
    return "Sin bloqueo"


def lock_status(user, now=None):
    return status_of(AccesoUsuario.objects.filter(user=user).first(), now)


def register_failure(user, now=None):
    now = now or timezone.now()
    AccesoUsuario.objects.get_or_create(user=user)
    with transaction.atomic():
        access = AccesoUsuario.objects.select_for_update().get(user=user)
        current = status_of(access, now)
        if current.is_locked:
            return current
        access.intentos_fallidos += 1
        access.ultimo_intento_fallido = now
        if access.intentos_fallidos >= settings.SECURITY_PERMANENT_LOCK_FAILURES:
            access.bloqueado = True
            access.bloqueado_desde = now
            access.bloqueado_hasta = None
            access._change_reason = "Bloqueo definitivo por intentos fallidos"
            access.save()
        elif access.intentos_fallidos == settings.SECURITY_TEMPORARY_LOCK_FAILURES:
            access.bloqueado_hasta = now + timedelta(minutes=settings.SECURITY_TEMPORARY_LOCK_MINUTES)
            access._change_reason = "Bloqueo temporal por intentos fallidos"
            access.save()
        else:
            AccesoUsuario.objects.filter(pk=access.pk).update(
                intentos_fallidos=access.intentos_fallidos,
                ultimo_intento_fallido=now,
                modified=now,
            )
        return status_of(access, now)


def register_login(user):
    AccesoUsuario.objects.filter(user=user, bloqueado=False).exclude(
        intentos_fallidos=0, bloqueado_hasta__isnull=True
    ).update(intentos_fallidos=0, bloqueado_hasta=None, modified=timezone.now())


def unlock(user, reason):
    access = AccesoUsuario.objects.filter(user=user).first()
    if not status_of(access).is_locked:
        return False
    access.intentos_fallidos = 0
    access.bloqueado = False
    access.bloqueado_desde = None
    access.bloqueado_hasta = None
    access._change_reason = reason
    access.save()
    return True
