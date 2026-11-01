import re
from decimal import ROUND_HALF_UP, Decimal

WHOLE_AMOUNT = re.compile(r"\d+|\d{1,3}(\.\d{3})+")


class Money:
    @staticmethod
    def round(value) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @classmethod
    def digits(cls, value) -> str:
        return f"{abs(cls.round(value)):,.0f}".replace(",", ".")

    @classmethod
    def format(cls, value) -> str:
        digits = cls.digits(value)
        return f"-${digits}" if cls.round(value) < 0 else f"${digits}"

    @staticmethod
    def parse(text) -> int:
        text = str(text).strip()
        if not WHOLE_AMOUNT.fullmatch(text):
            raise ValueError(text)
        return int(text.replace(".", ""))
