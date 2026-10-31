from decimal import Decimal

from django.db.models import DecimalField

from apps.payments.choices import EstadoDetallePago, TipoDetallePago

ZERO = Decimal("0")
MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
PREPAID_TYPES = (TipoDetallePago.RESERVA, TipoDetallePago.ANTICIPO)
RETAINED_STATES = (EstadoDetallePago.RETENIDO, EstadoDetallePago.RETENIDO_DEFINITIVO)
