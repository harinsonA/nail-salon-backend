from apps.payments.choices import EstadoDetallePago, TipoDetallePago


class PaymentDetail:
    @staticmethod
    def kind(detail):
        return detail.tipo_detalle or TipoDetallePago.ABONO

    @staticmethod
    def status(detail):
        return detail.estado_detalle or EstadoDetallePago.VIGENTE

    @classmethod
    def is_refund(cls, detail):
        return cls.kind(detail) == TipoDetallePago.DEVOLUCION

    @classmethod
    def is_reservation(cls, detail):
        return cls.kind(detail) == TipoDetallePago.RESERVA

    @classmethod
    def is_appointment_payment(cls, detail):
        return (
            not cls.is_refund(detail)
            and not cls.is_reservation(detail)
            and cls.status(detail) == EstadoDetallePago.VIGENTE
        )
