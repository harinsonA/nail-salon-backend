from apps.payments.choices import EstadoDetallePago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago


class PaymentRowFactory:
    def __init__(self, user, moment):
        self.user = user
        self.moment = moment

    @staticmethod
    def reference(method, reference):
        return None if method == MetodoPago.EFECTIVO else reference or None

    def build(self, payment, kind, amount, method, reference, **fields):
        return DetallePago(
            pago=payment,
            fecha_pago=self.moment,
            monto_pago=amount,
            metodo_pago=method,
            referencia_pago=self.reference(method, reference),
            registrado_por=self.user,
            tipo_detalle=kind,
            estado_detalle=EstadoDetallePago.VIGENTE,
            **fields,
        )

    def advance(self, payment, advance):
        return self.build(
            payment,
            TipoDetallePago.ANTICIPO,
            advance["amount"],
            advance["method"],
            advance["reference"],
        )

    def refund(self, row, refund):
        return self.build(
            row.pago,
            TipoDetallePago.DEVOLUCION,
            row.monto_pago,
            refund["method"],
            refund["reference"],
            detalle_devuelto=row,
        )

    def installment(self, payment, amount, method, reference, notes):
        return self.build(
            payment,
            TipoDetallePago.ABONO,
            amount,
            method,
            reference,
            notas_detalle=notes,
        )
