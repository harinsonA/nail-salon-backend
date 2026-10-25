from django_tenants.utils import get_public_schema_name, schema_context, schema_exists

from apps.common.claves import generar_clave_temporal
from apps.common.historial import sin_autor_de_la_peticion
from apps.profiles.models import Perfil
from apps.seguridad.access import lock_status, unlock

RESET_UNLOCK_REASON = "Desbloqueado al restablecer la clave desde el panel"
UNLOCK_REASON = "Desbloqueado desde el panel"
SYNC_REASON = "Datos del propietario actualizados desde el panel"
NAME_MAX_LENGTH = 150


def find_owner():
    return Perfil.objects.select_related("user").filter(rol=Perfil.Rol.PROPIETARIO).first()


def owner_user_data(persona):
    return {
        "first_name": persona.nombres[:NAME_MAX_LENGTH],
        "last_name": persona.apellidos[:NAME_MAX_LENGTH],
    }


def owner_profile_data(persona):
    return {
        "pais": persona.pais,
        "tipo_identificador_nacional": persona.tipo_identificador_nacional,
        "identificador_nacional": persona.identificador_nacional,
    }


def update_if_changed(instance, data):
    if all(getattr(instance, field) == value for field, value in data.items()):
        return False
    for field, value in data.items():
        setattr(instance, field, value)
    instance._change_reason = SYNC_REASON
    instance.save()
    return True


def apply_owner_data(perfil, persona):
    update_if_changed(perfil.user, owner_user_data(persona))
    update_if_changed(perfil, owner_profile_data(persona))


def sync_owner_data(persona):
    negocios = persona.negocios_como_titular.exclude(
        schema_name=get_public_schema_name()
    )
    for negocio in negocios:
        if not schema_exists(negocio.schema_name):
            continue
        with schema_context(negocio.schema_name), sin_autor_de_la_peticion():
            perfil = find_owner()
            if perfil is not None:
                apply_owner_data(perfil, persona)


def owner_lock_status(negocio):
    with schema_context(negocio.schema_name):
        perfil = find_owner()
        return lock_status(perfil.user) if perfil else None


def unlock_owner(negocio, usuario_del_panel=None):
    with schema_context(negocio.schema_name), sin_autor_de_la_peticion():
        perfil = find_owner()
        if perfil is None:
            return None
        unlocked = unlock(perfil.user, UNLOCK_REASON)
        correo = perfil.user.email
    if unlocked:
        negocio._change_reason = "Propietario desbloqueado"
        if usuario_del_panel is not None:
            negocio._history_user = usuario_del_panel
        negocio.save()
    return correo, unlocked


def restablecer_clave_del_propietario(negocio, usuario_del_panel=None):
    with schema_context(negocio.schema_name), sin_autor_de_la_peticion():
        perfil = find_owner()
        if perfil is None:
            return None
        clave = generar_clave_temporal()
        perfil.user.set_password(clave)
        perfil.user.save()
        perfil.debe_cambiar_clave = True
        perfil.save()
        unlock(perfil.user, RESET_UNLOCK_REASON)
        correo = perfil.user.email
    negocio._change_reason = "Clave del propietario restablecida"
    if usuario_del_panel is not None:
        negocio._history_user = usuario_del_panel
    negocio.save()
    return correo, clave
