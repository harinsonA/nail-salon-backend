from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name

from apps.tenancy.entorno_local import (
    ESQUEMA_LEGADO,
    exigir_debug,
    nombre_calificado,
    tablas_del_esquema,
    tablas_solo_de_negocio,
)


class Command(BaseCommand):
    help = (
        "Solo en desarrollo: mueve las tablas de negocio que quedaron en public, de antes del "
        "multi-tenant, a un esquema aparte, para que public quede como en producción."
    )

    def handle(self, *args, **options):
        exigir_debug()
        connection.set_schema_to_public()
        publico = get_public_schema_name()
        tablas = sorted(tablas_del_esquema(publico) & tablas_solo_de_negocio())
        if not tablas:
            self.stdout.write("No hay tablas de negocio en public. Nada que mover.")
            return

        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {connection.ops.quote_name(ESQUEMA_LEGADO)}")
            for tabla in tablas:
                cursor.execute(
                    f"ALTER TABLE {nombre_calificado(publico, tabla)} "
                    f"SET SCHEMA {connection.ops.quote_name(ESQUEMA_LEGADO)}"
                )

        for tabla in tablas:
            self.stdout.write(f"  {tabla}")
        self.stdout.write(self.style.SUCCESS(f"{len(tablas)} tablas movidas de public a «{ESQUEMA_LEGADO}»."))
