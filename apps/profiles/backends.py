from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.seguridad.access import lock_status, register_failure
from apps.seguridad.forms import LOCK_STATUS_ATTRIBUTE, LOCKED_USER_ATTRIBUTE


def remember_status(request, status, user):
    if request is not None:
        setattr(request, LOCK_STATUS_ATTRIBUTE, status)
        setattr(request, LOCKED_USER_ATTRIBUTE, user)


class CorreoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if password is None:
            return None
        users = get_user_model()._default_manager
        if connection.schema_name == get_public_schema_name():
            username = username if username is not None else kwargs.get(get_user_model().USERNAME_FIELD)
            if username is None:
                return None
            user = users.filter(**{get_user_model().USERNAME_FIELD: username}).first()
        else:
            correo = (username or kwargs.get("email") or "").strip()
            if not correo:
                return None
            user = users.filter(email__iexact=correo).first()
        return self.authenticate_with_lock(request, user, password)

    def authenticate_with_lock(self, request, user, password):
        if user is None:
            get_user_model()().set_password(password)
            return None
        status = lock_status(user)
        if status.is_locked:
            get_user_model()().set_password(password)
            remember_status(request, status, user)
            return None
        if user.check_password(password):
            return user if self.user_can_authenticate(user) else None
        remember_status(request, register_failure(user), user)
        return None
