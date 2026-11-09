UNLIMITED_LABEL = "sin límite"
LIMIT_TOO_LARGE = "El límite de usuarios no puede superar {maximum}."
LIMIT_TOO_SMALL = "El límite de usuarios debe ser al menos 1."
LIMIT_REQUIRED = "Escribe el límite de usuarios o marca «Sin límite»."
OVER_LIMIT_NOTICE = "Solo la propietaria podrá entrar hasta que desactive {excess}."


def accounts(count):
    return f"{count} cuenta" if count == 1 else f"{count} cuentas"
