class Scope:
    USER = "user"
    NEGOCIO = "negocio"

    CHOICES = (
        (USER, "Usuario"),
        (NEGOCIO, "Negocio"),
    )


class Category:
    SEGURIDAD = "seguridad"
    APARIENCIA = "apariencia"
    AGENDA = "agenda"

    CHOICES = (
        (SEGURIDAD, "Seguridad"),
        (APARIENCIA, "Apariencia"),
        (AGENDA, "Agenda"),
    )
