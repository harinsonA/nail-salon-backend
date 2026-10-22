from apps.appointments.models import Cita
from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de

"""========================================================================="""
# region ........ Helpers


def is_collaborator(user):
    return rol_de(user) == Perfil.Rol.COLABORADOR


def visible_appointments(user):
    appointments = Cita.objects.select_related("cliente", "creado_por", "asignado_a")
    return appointments.filter(asignado_a=user) if is_collaborator(user) else appointments


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class AppointmentAccessMixin:
    def get_queryset(self):
        return visible_appointments(self.request.user)


# endregion
"""========================================================================="""
