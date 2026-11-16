from apps.profiles.models import Perfil


class ProfileRules:
    LOCKED_MESSAGE = "La propietaria no puede editar sus datos personales."
    SAVED_MESSAGE = "Perfil actualizado exitosamente."

    def __init__(self, user):
        self.user = user

    @property
    def perfil(self):
        try:
            return self.user.perfil if self.user else None
        except Perfil.DoesNotExist:
            return None

    @property
    def rol(self):
        return self.perfil.rol if self.perfil else None

    @property
    def personal_data_locked(self):
        return self.rol == Perfil.Rol.PROPIETARIO

    @property
    def can_edit_personal_data(self):
        return self.perfil is not None and not self.personal_data_locked

    @property
    def full_name(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.username

    @property
    def initials(self):
        first = (self.user.first_name or "").strip()
        last = (self.user.last_name or "").strip()
        if first and last:
            return f"{first[0]}{last[0]}".upper()
        if first:
            return first[:2].upper()
        return (self.user.username or "?")[:2].upper()
