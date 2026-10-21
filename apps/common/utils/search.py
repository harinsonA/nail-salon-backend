import operator
from functools import reduce

from django.db.models import F, Func, Q, TextField, Value
from django.db.models.functions import Cast
from django.db.models.lookups import IContains

ACCENTED = "áéíóúüÁÉÍÓÚÜ"
PLAIN = "aeiouuAEIOUU"
ACCENT_TABLE = str.maketrans(ACCENTED, PLAIN)


class WithoutAccents(Func):
    function = "TRANSLATE"
    output_field = TextField()

    def __init__(self, expression):
        super().__init__(Cast(expression, TextField()), Value(ACCENTED), Value(PLAIN))


def without_accents(text):
    return text.translate(ACCENT_TABLE)


def contains_ignoring_accents(expression, value):
    if isinstance(expression, str):
        expression = F(expression)
    return IContains(WithoutAccents(expression), without_accents(value))


def search_ignoring_accents(fields, value):
    return reduce(operator.or_, (Q(contains_ignoring_accents(field, value)) for field in fields))
