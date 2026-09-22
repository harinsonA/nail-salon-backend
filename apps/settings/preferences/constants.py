class Scope:
    USER = "user"
    SALON = "salon"

    CHOICES = (
        (USER, "Usuario"),
        (SALON, "Salón"),
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
