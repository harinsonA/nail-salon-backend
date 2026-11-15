class Scope:
    USER = "user"
    NEGOCIO = "negocio"
    PLATAFORMA = "plataforma"

    CHOICES = (
        (USER, "Usuario"),
        (NEGOCIO, "Negocio"),
        (PLATAFORMA, "Plataforma"),
    )


class Category:
    SEGURIDAD = "seguridad"
    APARIENCIA = "apariencia"
    AGENDA = "agenda"
    FUNCIONES_NUEVAS = "funciones_nuevas"

    CHOICES = (
        (SEGURIDAD, "Seguridad"),
        (APARIENCIA, "Apariencia"),
        (AGENDA, "Agenda"),
        (FUNCIONES_NUEVAS, "Funciones nuevas"),
    )
