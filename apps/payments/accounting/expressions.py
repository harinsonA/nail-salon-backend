from django.db.models import Case, CharField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce, Greatest

from apps.payments.accounting.constants import (
    MONEY_FIELD,
    RETAINED_STATES,
    SERVICE_PREPAID_TYPES,
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
    def refundable_amount(rows, refunds, prefix=""):
        return Coalesce(
            Sum(
                Case(
                    When(rows, then=F(f"{prefix}monto_pago")),
                    When(
                        Q(**{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION}) & refunds,
                        then=-F(f"{prefix}monto_pago"),
                    ),
                    default=Value(ZERO),
                    output_field=MONEY_FIELD,
                )
            ),
            Value(ZERO),
            output_field=MONEY_FIELD,
        )

    @classmethod
    def retained_amount(cls, prefix=""):
        retained = {
            "tipo_detalle__in": SERVICE_PREPAID_TYPES,
            "estado_detalle__in": RETAINED_STATES,
        }
        return cls.refundable_amount(
            Q(**{f"{prefix}{field}": value for field, value in retained.items()}),
            Q(**{f"{prefix}detalle_devuelto__{field}": value for field, value in retained.items()}),
            prefix,
        )

    @classmethod
    def reservation_amount(cls, prefix=""):
        return cls.refundable_amount(
            Q(**{f"{prefix}tipo_detalle": TipoDetallePago.RESERVA}),
            Q(**{f"{prefix}detalle_devuelto__tipo_detalle": TipoDetallePago.RESERVA}),
            prefix,
        )

    @classmethod
    def appointment_payment_filter(cls, prefix=""):
        return (
            cls.incoming(prefix)
            & ~Q(**{f"{prefix}tipo_detalle": TipoDetallePago.RESERVA})
            & (
                Q(**{f"{prefix}estado_detalle": EstadoDetallePago.VIGENTE})
                | Q(**{f"{prefix}estado_detalle__isnull": True})
            )
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
        return (
            queryset.annotate(
                total_pagado=cls.net_paid(prefix),
                total_reserva=cls.reservation_amount(prefix),
                total_retenido=cls.retained_amount(prefix),
            )
            .annotate(
                total_aplicado=ExpressionWrapper(
                    F("total_pagado") - F("total_reserva"), output_field=MONEY_FIELD
                ),
            )
            .annotate(
                total_cita=ExpressionWrapper(
                    F("monto_total_cita") - F("total_retenido"), output_field=MONEY_FIELD
                ),
                total_abonado=ExpressionWrapper(
                    F("total_aplicado") - F("total_retenido"), output_field=MONEY_FIELD
                ),
                saldo_pendiente=Greatest(
                    F("monto_total_cita") - F("total_aplicado"),
                    Value(ZERO),
                    output_field=MONEY_FIELD,
                ),
            )
        )
