from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.settings.preferences import APP_MODULE
from apps.tenancy.entorno_local import exigir_debug
from apps.tenancy.models import Negocio


class Command(BaseCommand):
    help = "Solo en desarrollo: enciende o apaga la app móvil (preferencia app_module) de un negocio."

    def add_arguments(self, parser):
        parser.add_argument("negocio", help="Subdominio o esquema del negocio, por ejemplo demo.")
        parser.add_argument("--apagar", action="store_true", help="Apaga la app en vez de encenderla.")

    def handle(self, *args, negocio, apagar, **options):
        exigir_debug()
        connection.set_schema_to_public()
        esquema = negocio.strip().lower().replace("-", "_")
        encontrado = Negocio.objects.exclude(schema_name=get_public_schema_name()).filter(schema_name=esquema).first()
        if encontrado is None:
            raise CommandError(f"No hay ningún negocio «{negocio}».")
        with schema_context(encontrado.schema_name):
            APP_MODULE.set(not apagar)
            encendida = APP_MODULE.is_enabled()
        estado = "encendida" if encendida else "apagada"
        self.stdout.write(self.style.SUCCESS(f"«{encontrado.nombre}»: app móvil {estado}."))
