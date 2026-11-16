from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de


class LoginMessages:
    INVALID_LOGIN = "Correo o contraseña incorrectos."
    INACTIVE = "Esta cuenta está desactivada."
    UNLOCK_HINTS = {
        Perfil.Rol.PROPIETARIO: "pide ayuda al soporte de Hi Agenda",
        Perfil.Rol.ENCARGADO: "pide al propietario del negocio que te desbloquee",
    }
    DEFAULT_UNLOCK_HINT = "pide al propietario o a un encargado que te desbloquee"

    @classmethod
    def unlock_hint(cls, user):
        return cls.UNLOCK_HINTS.get(rol_de(user) if user else None, cls.DEFAULT_UNLOCK_HINT)
