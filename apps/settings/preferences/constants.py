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
    APP_MOVIL = "app_movil"

    CHOICES = (
        (SEGURIDAD, "Seguridad"),
        (APARIENCIA, "Apariencia"),
        (AGENDA, "Agenda"),
        (FUNCIONES_NUEVAS, "Funciones nuevas"),
        (APP_MOVIL, "App móvil"),
    )
