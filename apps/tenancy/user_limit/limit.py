from django.contrib.auth import get_user_model
from django.utils.functional import cached_property
from django_tenants.utils import schema_context, schema_exists

from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de
from apps.tenancy.models import Negocio
from apps.tenancy.user_limit.messages import UNLIMITED_LABEL


class UserLimit:
    def __init__(self, negocio):
        self.negocio = negocio

    @classmethod
    def for_request(cls, request):
        return cls(request.tenant)

    @classmethod
    def of(cls, negocio):
        if not schema_exists(negocio.schema_name):
            return None
        return cls(negocio)

    @property
    def limit(self):
        return self.negocio.limite_usuarios

    @property
    def is_unlimited(self):
        return self.limit is None

    @cached_property
    def active_count(self):
        with schema_context(self.negocio.schema_name):
            return get_user_model().objects.filter(is_active=True).count()

    @property
    def has_free_seat(self):
        return self.is_unlimited or self.active_count < self.limit

    @property
    def is_over_limit(self):
        return not self.is_unlimited and self.active_count > self.limit

    @property
    def excess(self):
        return self.active_count - self.limit if self.is_over_limit else 0

    @property
    def can_manage_members(self):
        return not self.is_over_limit

    @property
    def team_enabled(self):
        return self.is_unlimited or self.limit > 1 or self.active_count > 1

    @property
    def usage_label(self):
        limit = UNLIMITED_LABEL if self.is_unlimited else self.limit
        return f"{self.active_count} / {limit}"

    def lets_in(self, user):
        return not self.is_over_limit or rol_de(user) == Perfil.Rol.PROPIETARIO

    def lock(self):
        self.negocio = Negocio.objects.select_for_update().get(pk=self.negocio.pk)
        self.__dict__.pop("active_count", None)
        return self
