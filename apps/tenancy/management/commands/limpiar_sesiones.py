from django.core.management import call_command
from django.core.management.base import BaseCommand
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.esquemas import clasificar_negocios


class Command(BaseCommand):
    help = "Borra las sesiones vencidas de public y de cada negocio listo."

    def handle(self, *args, **options):
        listos, _ = clasificar_negocios()
        for esquema in [get_public_schema_name(), *listos]:
            with schema_context(esquema):
                call_command("clearsessions")
        self.stdout.write(f"Sesiones vencidas borradas. Esquemas revisados: {len(listos) + 1}.")
