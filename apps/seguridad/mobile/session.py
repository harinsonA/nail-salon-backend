import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.contrib.auth.models import update_last_login
from django.utils import timezone

from apps.common.middleware import get_daily_deadline
from apps.seguridad.access import LockStatus, lock_status, register_login
from apps.seguridad.mobile import messages
from apps.seguridad.models import SesionMovil
from apps.seguridad.sessions import locked_session_message

LAST_USE_REFRESH_SECONDS = 60


class MobileSessionError(Exception):
    def __init__(self, code, message, lock: LockStatus | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.lock = lock


@dataclass(frozen=True)
class IssuedKey:
    key: str
    expires_at: datetime


class MobileSession:
    DEVICE_KEY_DAYS = 30
    LOGIN_REASON = "Ingreso con clave"
    REFRESH_REASON = "Renovación con huella"
    BIOMETRIC_ON_REASON = "Huella activada"
    BIOMETRIC_OFF_REASON = "Huella desactivada"
    LOGOUT_REASON = "Cierre de sesión"
    REVOKE_REASON = "Sesión anulada"
    PASSWORD_REASON = "Cambio de clave"

    def __init__(self, sesion):
        self.sesion = sesion
        self.session_key = None

    @staticmethod
    def digest(key):
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def new_key(user):
        return f"{user.pk}.{secrets.token_urlsafe(32)}"

    @staticmethod
    def user_pk_of(key):
        prefix = key.partition(".")[0]
        return int(prefix) if prefix.isdigit() else None

    @property
    def user(self):
        return self.sesion.user

    @property
    def has_device_key(self):
        vence = self.sesion.llave_telefono_vence
        return bool(self.sesion.llave_telefono and vence and vence > timezone.now())

    @classmethod
    def log_in(cls, user, device, app_version):
        sesion, _ = SesionMovil.objects.get_or_create(user=user)
        session = cls(sesion)
        same_device = bool(device) and device == sesion.dispositivo
        if not (same_device and session.has_device_key):
            sesion.llave_telefono = None
            sesion.llave_telefono_vence = None
        sesion.dispositivo = device or None
        session.issue_session_key(app_version, cls.LOGIN_REASON)
        register_login(user)
        update_last_login(None, user)
        return session

    @classmethod
    def refresh(cls, device_key, app_version, admit):
        sesion = SesionMovil.objects.select_related("user").filter(llave_telefono=cls.digest(device_key)).first()
        session = cls(sesion) if sesion else None
        if session is None or not session.has_device_key:
            raise MobileSessionError("session_required", messages.DEVICE_KEY_INVALID)
        session.check_account()
        admit(session.user)
        sesion.llave_telefono_vence = timezone.now() + timedelta(days=cls.DEVICE_KEY_DAYS)
        session.issue_session_key(app_version, cls.REFRESH_REASON)
        register_login(session.user)
        return session

    @classmethod
    def authenticate(cls, key, device, app_version):
        sesion = SesionMovil.objects.select_related("user").filter(llave_sesion=cls.digest(key)).first()
        if sesion is None:
            raise cls.missing_key_error(key, device)
        session = cls(sesion)
        if sesion.llave_sesion_vence is None or sesion.llave_sesion_vence <= timezone.now():
            raise MobileSessionError("session_expired", messages.SESSION_EXPIRED)
        session.check_account()
        session.touch(app_version)
        return session

    @classmethod
    def missing_key_error(cls, key, device):
        user_pk = cls.user_pk_of(key)
        current = SesionMovil.objects.filter(user_id=user_pk).first() if user_pk else None
        if current and current.llave_sesion and current.dispositivo and current.dispositivo != device:
            return MobileSessionError("session_closed_elsewhere", messages.SESSION_CLOSED_ELSEWHERE)
        return MobileSessionError("session_required", messages.SESSION_ENDED)

    def issue_session_key(self, app_version, reason):
        key = self.new_key(self.user)
        self.sesion.llave_sesion = self.digest(key)
        self.sesion.llave_sesion_vence = get_daily_deadline()
        self.sesion.firma_clave = self.user.get_session_auth_hash()
        self.sesion.version_app = app_version or self.sesion.version_app
        self.sesion.ultimo_uso = timezone.now()
        self.sesion._change_reason = reason
        self.sesion.save()
        self.session_key = IssuedKey(key, self.sesion.llave_sesion_vence)
        return self.session_key

    def check_account(self):
        status = lock_status(self.user)
        if status.is_locked:
            self.revoke(self.REVOKE_REASON)
            raise MobileSessionError("account_locked", locked_session_message(status), status)
        if not self.user.is_active or self.sesion.firma_clave != self.user.get_session_auth_hash():
            self.revoke(self.REVOKE_REASON)
            raise MobileSessionError("session_required", messages.SESSION_ENDED)

    def touch(self, app_version):
        now = timezone.now()
        last_use = self.sesion.ultimo_uso
        changes = {}
        if not last_use or (now - last_use).total_seconds() >= LAST_USE_REFRESH_SECONDS:
            changes["ultimo_uso"] = now
        if app_version and app_version != self.sesion.version_app:
            changes["version_app"] = app_version
        if changes:
            SesionMovil.objects.filter(pk=self.sesion.pk).update(**changes)

    def enable_biometric(self):
        key = self.new_key(self.user)
        self.sesion.llave_telefono = self.digest(key)
        self.sesion.llave_telefono_vence = timezone.now() + timedelta(days=self.DEVICE_KEY_DAYS)
        self.sesion._change_reason = self.BIOMETRIC_ON_REASON
        self.sesion.save()
        return IssuedKey(key, self.sesion.llave_telefono_vence)

    def disable_biometric(self):
        self.sesion.llave_telefono = None
        self.sesion.llave_telefono_vence = None
        self.sesion._change_reason = self.BIOMETRIC_OFF_REASON
        self.sesion.save()

    def revoke(self, reason):
        if not (self.sesion.llave_sesion or self.sesion.llave_telefono):
            return
        self.sesion.llave_sesion = None
        self.sesion.llave_sesion_vence = None
        self.sesion.llave_telefono = None
        self.sesion.llave_telefono_vence = None
        self.sesion._change_reason = reason
        self.sesion.save()

    def log_out(self):
        self.revoke(self.LOGOUT_REASON)

    def password_changed(self):
        self.sesion.firma_clave = self.user.get_session_auth_hash()
        self.sesion._change_reason = self.PASSWORD_REASON
        self.sesion.save()
