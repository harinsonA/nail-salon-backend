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


def format_full_date(date_obj) -> str:
    """
    Formatea una fecha en español, ejemplo: Lunes 5 de Marzo del 2022
    """
    if not date_obj:
        return ""

    day_name = DAY_OF_WEEK_TO_NAME[date_obj.weekday()]
    day = date_obj.day
    month_name = MONTH_NUMBER_TO_NAME[date_obj.month]
    year = date_obj.year

    return f"{day_name} {day} de {month_name} del {year}"
