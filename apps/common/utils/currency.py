from decimal import Decimal


def format_currency(value) -> str:
    value = value or Decimal("0")
    return f"$ {value:,.0f}"


def format_money(value) -> str:
    amount = f"{abs(value or 0):,.0f}".replace(",", ".")
    return f"-${amount}" if (value or 0) < 0 else f"${amount}"
