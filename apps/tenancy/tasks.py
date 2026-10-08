from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context, schema_exists

from apps.profiles.models import Perfil
from apps.settings.models import ConfiguracionNegocio
from apps.tenancy.models import Negocio


@shared_task
def preparar_negocio(negocio_id, correo, hash_clave=None):
    connection.set_schema_to_public()
    negocio = Negocio.objects.get(pk=negocio_id)
    try:
        if schema_exists(negocio.schema_name):
            call_command("migrate_schemas", schema_name=negocio.schema_name, interactive=False, verbosity=0)
        else:
            negocio.create_schema(check_if_exists=True, verbosity=0)
        with schema_context(negocio.schema_name):
            crear_propietario(negocio, correo, hash_clave)
            ConfiguracionNegocio.objects.get_or_create(defaults={"nombre_visible": negocio.nombre})
    except Exception as exc:
        negocio.error_preparacion = f"{type(exc).__name__}: {exc}"
        negocio._change_reason = "La preparación falló"
        negocio.save()
        raise
    negocio.estado = Negocio.Estado.ACTIVO
    negocio.error_preparacion = None
    negocio._change_reason = "Alta terminada"
    negocio.save()


def crear_propietario(negocio, correo, hash_clave):
    usuario = get_user_model().objects.filter(email__iexact=correo).first()
    if usuario is None:
        usuario = get_user_model()(
            username=correo[:150],
            email=correo,
            first_name=negocio.titular.nombres[:150],
            last_name=negocio.titular.apellidos[:150],
        )
        if hash_clave:
            usuario.password = hash_clave
        else:
            usuario.set_unusable_password()
        usuario.save()
    perfil = usuario.perfil
    if not Perfil.objects.filter(rol=Perfil.Rol.PROPIETARIO).exclude(user=usuario).exists():
        perfil.rol = Perfil.Rol.PROPIETARIO
    perfil.debe_cambiar_clave = True
    perfil.save()
