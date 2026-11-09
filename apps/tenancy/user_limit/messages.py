UNLIMITED_LABEL = "sin límite"
LIMIT_TOO_LARGE = "El límite de usuarios no puede superar {maximum}."
LIMIT_TOO_SMALL = "El límite de usuarios debe ser al menos 1."
LIMIT_REQUIRED = "Escribe el límite de usuarios o marca «Sin límite»."
OVER_LIMIT_NOTICE = "Solo la propietaria podrá entrar hasta que desactive {excess}."
NO_FREE_SEAT = (
    "Llegaste al límite de {limit}. Para sumar a alguien, desactiva una cuenta "
    "o pide a Hi Agenda ampliar el límite."
)
OVER_LIMIT_LOGIN = (
    "Este negocio tiene más cuentas activas que su límite de usuarios. "
    "Por ahora solo entra el propietario: pídele que ajuste el equipo."
)
OVER_LIMIT_MEMBER_ACTION = (
    "Mientras el negocio tenga más cuentas activas que su límite, en Equipo solo "
    "se puede desactivar: faltan {excess}."
)
TEAM_DISABLED = "Este negocio no tiene sección Equipo."


def accounts(count):
    return f"{count} cuenta" if count == 1 else f"{count} cuentas"


def active_accounts(count):
    return f"{accounts(count)} activa" if count == 1 else f"{accounts(count)} activas"


def seat_refusal(user_limit):
    if user_limit.is_over_limit:
        return OVER_LIMIT_MEMBER_ACTION.format(excess=accounts(user_limit.excess))
    return NO_FREE_SEAT.format(limit=active_accounts(user_limit.limit))
