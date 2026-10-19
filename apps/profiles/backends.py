from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.seguridad.access import lock_status, register_failure
from apps.seguridad.forms import LOCK_STATUS_ATTRIBUTE


def remember_status(request, status):
    if request is not None:
        setattr(request, LOCK_STATUS_ATTRIBUTE, status)


class CorreoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if connection.schema_name == get_public_schema_name():
            return self.authenticate_panel(request, username, password, **kwargs)
        correo = (username or kwargs.get("email") or "").strip()
        if not correo or password is None:
            return None
        usuario = get_user_model()._default_manager.filter(email__iexact=correo).first()
        if usuario is None:
            get_user_model()().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None

    def authenticate_panel(self, request, username, password, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        user = User._default_manager.filter(**{User.USERNAME_FIELD: username}).first()
        if user is None:
            User().set_password(password)
            return None
        status = lock_status(user)
        if status.is_locked:
            User().set_password(password)
            remember_status(request, status)
            return None
        if user.check_password(password):
            return user if self.user_can_authenticate(user) else None
        remember_status(request, register_failure(user))
        return None
