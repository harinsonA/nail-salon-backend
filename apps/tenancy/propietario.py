from django_tenants.utils import schema_context

from apps.common.claves import generar_clave_temporal
from apps.common.historial import sin_autor_de_la_peticion
from apps.profiles.models import Perfil


def restablecer_clave_del_propietario(negocio, usuario_del_panel=None):
    with schema_context(negocio.schema_name), sin_autor_de_la_peticion():
        perfil = Perfil.objects.select_related("user").filter(rol=Perfil.Rol.PROPIETARIO).first()
        if perfil is None:
            return None
        clave = generar_clave_temporal()
        perfil.user.set_password(clave)
        perfil.user.save()
        perfil.debe_cambiar_clave = True
        perfil.save()
        correo = perfil.user.email
    negocio._change_reason = "Clave del propietario restablecida"
    if usuario_del_panel is not None:
        negocio._history_user = usuario_del_panel
    negocio.save()
    return correo, clave
