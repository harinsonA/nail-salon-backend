from django.db.models import ExpressionWrapper, F, Sum

from apps.payments.accounting.constants import MONEY_FIELD, ZERO


class ServiceLines:
    @staticmethod
    def subtotal(price, quantity):
        return price * quantity

    @staticmethod
    def subtotal_expression():
        return ExpressionWrapper(
            F("precio_servicio") * F("cantidad_servicios"), output_field=MONEY_FIELD
        )

    @classmethod
    def total(cls, price, quantity, discount):
        return cls.subtotal(price, quantity) - discount

    @classmethod
    def accepts_discount(cls, price, quantity, discount):
        return 0 <= discount <= cls.subtotal(price, quantity)

    @classmethod
    def amounts(cls, appointment):
        totals = appointment.detalles.aggregate(
            subtotal=Sum(cls.subtotal_expression()),
            discounts=Sum("descuento"),
            total=Sum("precio_acordado"),
        )
        return (
            totals["subtotal"] or ZERO,
            totals["discounts"] or ZERO,
            totals["total"] or ZERO,
        )
