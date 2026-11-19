from apps.payments.accounting.expressions import PaymentExpressions
from apps.payments.models import DetallePago


class CollectedIncome:
    @staticmethod
    def between(start, end):
        return DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__date__gte=start,
            fecha_pago__date__lt=end,
        ).aggregate(total=PaymentExpressions.net_paid())["total"]
