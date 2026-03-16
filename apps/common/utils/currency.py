from decimal import Decimal


def format_currency(value) -> str:
    value = value or Decimal("0")
    return f"$ {value:,.0f}"
