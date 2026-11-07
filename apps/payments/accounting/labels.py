from apps.payments.choices import EstadoDetallePago, MetodoPago, TipoDetallePago, TipoMovimiento


class PaymentLabels:
    METHODS = dict(MetodoPago.CHOICES)
    KINDS = dict(TipoDetallePago.CHOICES)
    MOVEMENTS = dict(TipoMovimiento.CHOICES)
    REFUND_METHODS = (MetodoPago.EFECTIVO, MetodoPago.TRANSFERENCIA)
    RESERVATION_STATUS = {
        EstadoDetallePago.VIGENTE: "Pagada",
        EstadoDetallePago.RETENIDO: "Retenida",
        EstadoDetallePago.RETENIDO_DEFINITIVO: "Retenida",
        EstadoDetallePago.DEVUELTO: "Reembolsada",
    }

    @classmethod
    def method(cls, code):
        return cls.METHODS.get(code, code)

    @classmethod
    def kind(cls, code):
        return cls.KINDS[code or TipoDetallePago.ABONO]

    @classmethod
    def movement(cls, code):
        return cls.MOVEMENTS.get(code, code)

    @classmethod
    def reservation_status(cls, code):
        return cls.RESERVATION_STATUS[code or EstadoDetallePago.VIGENTE]

    @classmethod
    def refund_choices(cls):
        return [(code, cls.METHODS[code]) for code in cls.REFUND_METHODS]
