from django.db.models import Case, CharField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce, Greatest

from apps.payments.accounting.constants import (
    MONEY_FIELD,
    PREPAID_TYPES,
    RETAINED_STATES,
    ZERO,
)
from apps.payments.choices import EstadoDetallePago, TipoDetallePago, TipoMovimiento


class PaymentExpressions:
    @staticmethod
    def signed_amount(prefix=""):
        return Case(
            When(
                **{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION},
                then=-F(f"{prefix}monto_pago"),
            ),
            default=F(f"{prefix}monto_pago"),
            output_field=MONEY_FIELD,
        )

    @classmethod
    def net_paid(cls, prefix=""):
        return Coalesce(
            Sum(cls.signed_amount(prefix)), Value(ZERO), output_field=MONEY_FIELD
        )

    @staticmethod
    def incoming(prefix=""):
        return ~Q(**{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION})

    @staticmethod
    def retained_amount(prefix=""):
        retained = Q(
            **{
                f"{prefix}tipo_detalle__in": PREPAID_TYPES,
                f"{prefix}estado_detalle__in": RETAINED_STATES,
            }
        )
        refund_of_retained = Q(
            **{
                f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION,
                f"{prefix}detalle_devuelto__estado_detalle__in": RETAINED_STATES,
            }
        )
        return Coalesce(
            Sum(
                Case(
                    When(retained, then=F(f"{prefix}monto_pago")),
                    When(refund_of_retained, then=-F(f"{prefix}monto_pago")),
                    default=Value(ZERO),
                    output_field=MONEY_FIELD,
                )
            ),
            Value(ZERO),
            output_field=MONEY_FIELD,
        )

    @classmethod
    def appointment_payment_filter(cls, prefix=""):
        return cls.incoming(prefix) & (
            Q(**{f"{prefix}estado_detalle": EstadoDetallePago.VIGENTE})
            | Q(**{f"{prefix}estado_detalle__isnull": True})
        )

    @staticmethod
    def movement_kind(prefix=""):
        return Case(
            When(
                **{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION},
                then=Value(TipoMovimiento.EGRESO),
            ),
            default=Value(TipoMovimiento.INGRESO),
            output_field=CharField(),
        )

    @classmethod
    def with_appointment_summary(cls, queryset, prefix="detalles_pago__"):
        return queryset.annotate(
            total_pagado=cls.net_paid(prefix),
            total_retenido=cls.retained_amount(prefix),
        ).annotate(
            total_cita=ExpressionWrapper(
                F("monto_total_cita") - F("total_retenido"), output_field=MONEY_FIELD
            ),
            total_abonado=ExpressionWrapper(
                F("total_pagado") - F("total_retenido"), output_field=MONEY_FIELD
            ),
            saldo_pendiente=Greatest(
                F("monto_total_cita") - F("total_pagado"),
                Value(ZERO),
                output_field=MONEY_FIELD,
            ),
        )
