from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.tenancy.alta import correo_de_acceso
from apps.tenancy.models import Negocio
from apps.tenancy.tasks import preparar_negocio


class Command(BaseCommand):
    help = (
        "Retoma el alta de un negocio que quedó en «preparando»: crea o completa su esquema, el propietario "
        "y la configuración. Corre aquí mismo, sin pasar por Celery, y se puede repetir."
    )

    def add_arguments(self, parser):
        parser.add_argument("negocio", help="Subdominio o esquema del negocio, por ejemplo mi-barberia.")

    def handle(self, *args, negocio, **options):
        connection.set_schema_to_public()
        esquema = negocio.strip().lower().replace("-", "_")
        encontrado = Negocio.objects.exclude(schema_name=get_public_schema_name()).filter(schema_name=esquema).first()
        if encontrado is None:
            raise CommandError(f"No hay ningún negocio «{negocio}».")
        if encontrado.estado != Negocio.Estado.PREPARANDO:
            raise CommandError(f"«{encontrado.nombre}» está {encontrado.get_estado_display().lower()}: no hay alta que reparar.")
        correo = correo_de_acceso(encontrado.titular)
        if correo is None:
            raise CommandError("El titular no tiene correo: agrégale uno en su ficha antes de reparar.")
        try:
            preparar_negocio(encontrado.pk, correo, None)
        except Exception as error:
            raise CommandError(f"La reparación falló: {error}") from error
        self.stdout.write(
            self.style.SUCCESS(
                f"«{encontrado.nombre}» quedó activo. Si su propietario no tenía clave, restablécela desde el panel."
            )
        )
