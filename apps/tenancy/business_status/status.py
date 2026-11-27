from typing import NamedTuple

from django_tenants.utils import get_public_schema_name

from apps.profiles.permisos import (
    CREAR_CITAS_EN_PAUSA_CON_MOROSO,
    EN_PAUSA_CON_MOROSO,
    administra_el_negocio,
)
from apps.tenancy.business_status import messages
from apps.tenancy.models import Negocio


class Unavailable(NamedTuple):
    status_code: int
    title: str
    message: str


UNAVAILABLE = {
    Negocio.Estado.PREPARANDO: Unavailable(503, messages.PREPARING_TITLE, messages.PREPARING_MESSAGE),
    Negocio.Estado.PAUSADO: Unavailable(410, messages.PAUSED_TITLE, messages.PAUSED_MESSAGE),
    Negocio.Estado.CANCELADO: Unavailable(410, messages.CANCELLED_TITLE, messages.CANCELLED_MESSAGE),
}


class BusinessStatus:
    PAYMENT_PENDING_STATUS = 402

    def __init__(self, negocio):
        self.negocio = negocio

    @classmethod
    def for_request(cls, request):
        negocio = getattr(request, "tenant", None)
        if negocio is None or negocio.schema_name == get_public_schema_name():
            return None
        return cls(negocio)

    @property
    def unavailable(self):
        return UNAVAILABLE.get(self.negocio.estado)

    @property
    def is_overdue(self):
        return self.negocio.estado == Negocio.Estado.MOROSO

    @property
    def allows_new_appointments(self):
        return not self.is_overdue

    def pauses_section(self, url_name, user):
        if not self.is_overdue:
            return False
        if url_name in CREAR_CITAS_EN_PAUSA_CON_MOROSO:
            return True
        return url_name in EN_PAUSA_CON_MOROSO and administra_el_negocio(user)
