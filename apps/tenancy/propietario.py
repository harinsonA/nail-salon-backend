from django_tenants.utils import schema_context

from apps.common.claves import generar_clave_temporal
from apps.common.historial import sin_autor_de_la_peticion
from apps.profiles.models import Perfil
from apps.seguridad.access import lock_status, unlock

RESET_UNLOCK_REASON = "Desbloqueado al restablecer la clave desde el panel"
UNLOCK_REASON = "Desbloqueado desde el panel"


def find_owner():
    return Perfil.objects.select_related("user").filter(rol=Perfil.Rol.PROPIETARIO).first()


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
