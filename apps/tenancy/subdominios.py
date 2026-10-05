import re

from django.core.exceptions import ValidationError

LARGO_MINIMO = 3
LARGO_MAXIMO = 40
PATRON = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RESERVADOS = frozenset(
    {
        "admin",
        "api",
        "app",
        "ayuda",
        "blog",
        "cdn",
        "correo",
        "docs",
        "ftp",
        "imap",
        "mail",
        "media",
        "pop",
        "public",
        "smtp",
        "soporte",
        "static",
        "status",
        "www",
    }
)


def validar_subdominio(subdominio):
    if not LARGO_MINIMO <= len(subdominio) <= LARGO_MAXIMO:
        raise ValidationError(
            "El subdominio debe tener entre %(minimo)s y %(maximo)s caracteres.",
            params={"minimo": LARGO_MINIMO, "maximo": LARGO_MAXIMO},
        )
    if not PATRON.match(subdominio):
        raise ValidationError(
            "El subdominio solo admite letras minúsculas sin tilde, números y guiones "
            "sueltos entre ellos, y debe empezar con una letra."
        )
    if subdominio in RESERVADOS or subdominio.startswith("pg-"):
        raise ValidationError("«%(subdominio)s» está reservado.", params={"subdominio": subdominio})


def esquema_desde_subdominio(subdominio):
    validar_subdominio(subdominio)
    return subdominio.replace("-", "_")


def validar_esquema(esquema):
    if "-" in esquema:
        raise ValidationError("El nombre del esquema no admite guiones.")
    validar_subdominio(esquema.replace("_", "-"))
