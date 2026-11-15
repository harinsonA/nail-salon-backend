from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.appointments.access import is_collaborator
from apps.clients.models import Cliente

User = get_user_model()


class AppointmentAssignment:
    def __init__(self, user):
        self.user = user
        self.collaborator = is_collaborator(user)

    @property
    def can_change_saved(self):
        return not self.collaborator

    def staff(self, current=None):
        if self.collaborator:
            return User.objects.filter(pk=self.user.pk)
        condition = Q(is_active=True, perfil__isnull=False)
        if current:
            condition |= Q(pk=current.pk)
        return User.objects.filter(condition).order_by(
            "first_name", "last_name", "email"
        )

    @staticmethod
    def clients(current=None):
        condition = Q(pk__in=Cliente.activos.values("pk"))
        if current:
            condition |= Q(pk=current.pk)
        return Cliente.objects.filter(condition).order_by("nombre", "apellido")

    def resolve(self, chosen):
        return self.user if self.collaborator else chosen
