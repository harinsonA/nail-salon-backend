import re
from zoneinfo import available_timezones

from result import Err, Ok, Result

"""========================================================================="""
# region ........ Constants


BUSINESS_NAME_MIN_LENGTH = 3
BUSINESS_NAME_MAX_LENGTH = 40
SUBDOMAIN_PATTERN = re.compile(r"^[a-z]+(-[a-z]+)*$")
SCHEMA_PATTERN = re.compile(r"^[a-z]+(_[a-z]+)*$")
RESERVED_NAMES = frozenset(
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
        "legado",
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


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Classes


class BusinessCleaner:
    @staticmethod
    def clean_subdomain_field(field_value: str) -> Result[str, str]:
        value = field_value.strip()
        if not BUSINESS_NAME_MIN_LENGTH <= len(value) <= BUSINESS_NAME_MAX_LENGTH:
            return Err(
                f"El subdominio debe tener entre {BUSINESS_NAME_MIN_LENGTH} y "
                f"{BUSINESS_NAME_MAX_LENGTH} caracteres."
            )
        if not SUBDOMAIN_PATTERN.match(value):
            return Err(
                "El subdominio solo admite letras minúsculas sin tilde, separadas con un guion "
                "(por ejemplo, el-corte)."
            )
        if value in RESERVED_NAMES or value.startswith("pg-"):
            return Err(f"«{value}» está reservado.")
        return Ok(value)

    @staticmethod
    def clean_schema_field(field_value: str) -> Result[str, str]:
        value = field_value.strip()
        if not BUSINESS_NAME_MIN_LENGTH <= len(value) <= BUSINESS_NAME_MAX_LENGTH:
            return Err(
                f"El esquema debe tener entre {BUSINESS_NAME_MIN_LENGTH} y "
                f"{BUSINESS_NAME_MAX_LENGTH} caracteres."
            )
        if not SCHEMA_PATTERN.match(value):
            return Err(
                "El esquema solo admite letras minúsculas sin tilde, separadas con un guion bajo "
                "(por ejemplo, el_corte)."
            )
        if value.replace("_", "-") in RESERVED_NAMES or value.startswith("pg_"):
            return Err(f"«{value}» está reservado.")
        return Ok(value)

    @staticmethod
    def clean_time_zone_field(field_value: str) -> Result[str, str]:
        value = field_value.strip()
        if value not in available_timezones():
            return Err(f"«{value}» no es una zona horaria válida.")
        return Ok(value)


# endregion
"""========================================================================="""
