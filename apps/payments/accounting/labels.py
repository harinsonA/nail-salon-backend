from apps.payments.choices import MetodoPago, TipoDetallePago, TipoMovimiento


class PaymentLabels:
    METHODS = dict(MetodoPago.CHOICES)
    KINDS = dict(TipoDetallePago.CHOICES)
    MOVEMENTS = dict(TipoMovimiento.CHOICES)
    REFUND_METHODS = (MetodoPago.EFECTIVO, MetodoPago.TRANSFERENCIA)

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
    def refund_choices(cls):
        return [(code, cls.METHODS[code]) for code in cls.REFUND_METHODS]
