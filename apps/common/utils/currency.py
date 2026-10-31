from decimal import ROUND_HALF_UP, Decimal


class Money:
    @staticmethod
    def format(value) -> str:
        amount = Decimal(value or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        digits = f"{abs(amount):,.0f}".replace(",", ".")
        return f"-${digits}" if amount < 0 else f"${digits}"
