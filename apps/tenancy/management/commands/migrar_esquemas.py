from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.tenancy.esquemas import clasificar_negocios


class Command(BaseCommand):
    help = (
        "Migra public y los negocios listos. Omite los que siguen preparándose o no tienen esquema: "
        "de esos se encarga su tarea de alta, y así un alta a medias no bloquea el arranque."
    )

    def handle(self, *args, **options):
        verbosidad = options["verbosity"]
        call_command("migrate_schemas", shared=True, interactive=False, verbosity=verbosidad)
        listos, omitidos = clasificar_negocios()
        for esquema in listos:
            call_command("migrate_schemas", schema_name=esquema, interactive=False, verbosity=verbosidad)
        for esquema in omitidos:
            self.stdout.write(self.style.WARNING(f"Se omite «{esquema}»: sigue preparándose o no tiene esquema."))
