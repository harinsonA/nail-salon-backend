from django.utils import timezone

from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME


DAY_OF_WEEK_TO_NAME = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


def format_plain_date(date_obj) -> str:
    return f"{date_obj.day} {MONTH_NUMBER_TO_NAME[date_obj.month].lower()} {date_obj.year}"


def format_long_date(date_obj) -> str:
    return f"{DAY_OF_WEEK_TO_NAME[date_obj.weekday()]} {format_plain_date(date_obj)}"


def format_date_time(datetime_obj) -> str:
    local = timezone.localtime(datetime_obj)
    return f"{format_plain_date(local)}, {local.strftime('%H:%M')}"


def format_short_date_time(datetime_obj) -> str:
    if not datetime_obj:
        return "-- --"
    return timezone.localtime(datetime_obj).strftime("%d/%m/%Y %H:%M")
