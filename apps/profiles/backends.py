from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name


class CorreoBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if connection.schema_name == get_public_schema_name():
            return super().authenticate(request, username=username, password=password, **kwargs)
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
