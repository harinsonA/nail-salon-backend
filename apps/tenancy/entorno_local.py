from django.apps import apps
from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection

ESQUEMA_LEGADO = "legado"
ESQUEMA_DEMO = "demo"
TABLAS_RENOMBRADAS = {"configuracion_salon": "configuracion_negocio"}
COLUMNAS_RENOMBRADAS = {"configuracion_negocio": {"nombre_salon": "nombre_visible"}}


def exigir_debug():
    if not settings.DEBUG:
        raise CommandError("Este comando es solo para desarrollo: requiere DEBUG=True.")


def configuraciones_solo_de_negocio():
    nombres = [app for app in settings.TENANT_APPS if app not in settings.SHARED_APPS]
    return [config for config in apps.get_app_configs() if config.name in nombres]


def tablas_solo_de_negocio():
    tablas = {
        modelo._meta.db_table
        for config in configuraciones_solo_de_negocio()
        for modelo in config.get_models(include_auto_created=True)
    }
    return tablas | set(TABLAS_RENOMBRADAS)


def tablas_del_esquema(esquema):
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = %s", [esquema])
        return {fila[0] for fila in cursor.fetchall()}


def columnas_de(esquema, tabla):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            [esquema, tabla],
        )
        return [fila[0] for fila in cursor.fetchall()]


def nombre_calificado(esquema, tabla):
    return f"{connection.ops.quote_name(esquema)}.{connection.ops.quote_name(tabla)}"
