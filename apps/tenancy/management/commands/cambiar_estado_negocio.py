from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.tenancy.estados import cambiar_estado
from apps.tenancy.models import Negocio


class Command(BaseCommand):
    help = "Cambia el estado de un negocio (moroso, pausado, cancelado o activo) dejando el motivo en su historial."

    def add_arguments(self, parser):
        parser.add_argument("negocio", help="Subdominio o esquema del negocio, por ejemplo mi-barberia.")
        parser.add_argument("estado", choices=[estado.value for estado in Negocio.Estado])
        parser.add_argument("--motivo", required=True, help="Por qué cambia: queda en el historial.")

    def handle(self, *args, negocio, estado, motivo, **options):
        connection.set_schema_to_public()
        esquema = negocio.strip().lower().replace("-", "_")
        encontrado = Negocio.objects.exclude(schema_name=get_public_schema_name()).filter(schema_name=esquema).first()
        if encontrado is None:
            raise CommandError(f"No hay ningún negocio «{negocio}».")
        anterior = encontrado.get_estado_display()
        try:
            cambiar_estado(encontrado, estado, motivo)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages))
        self.stdout.write(
            self.style.SUCCESS(f"«{encontrado.nombre}»: {anterior} → {encontrado.get_estado_display()}.")
        )
