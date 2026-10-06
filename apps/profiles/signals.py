from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db import connection
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django_tenants.utils import get_public_schema_name

from apps.common.middleware import start_session_window
from apps.settings.preferences import SESSION_IDLE_MINUTES


@receiver(user_logged_in)
def start_user_session_window(sender, request, user, **kwargs):
    start_session_window(request.session, SESSION_IDLE_MINUTES.get(user) * 60)


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def guardar_correo_en_minusculas(sender, instance, **kwargs):
    instance.email = (instance.email or "").strip().lower()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_de_colaborador(sender, instance, created, raw=False, **kwargs):
    if not created or raw or connection.schema_name == get_public_schema_name():
        return
    from apps.profiles.models import Perfil

    Perfil.objects.get_or_create(user=instance)
