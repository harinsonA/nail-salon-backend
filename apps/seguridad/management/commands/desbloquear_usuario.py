from contextlib import nullcontext

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.seguridad.access import unlock
from apps.tenancy.models import Negocio

REASON = "Desbloqueado con el comando desbloquear_usuario"


class Command(BaseCommand):
    help = (
        "Desbloquea una cuenta bloqueada por intentos fallidos. Sin --negocio busca un usuario del panel por su "
        "nombre de usuario; con --negocio, un usuario de ese negocio por su correo."
    )

    def add_arguments(self, parser):
        parser.add_argument("usuario", help="Usuario del panel, o el correo de la persona si se indica --negocio.")
        parser.add_argument("--negocio", help="Subdominio o esquema del negocio, por ejemplo mi-barberia.")

    def handle(self, *args, usuario, negocio=None, **options):
        connection.set_schema_to_public()
        identifier = usuario.strip()
        business = self.find_business(negocio) if negocio else None
        with schema_context(business.schema_name) if business else nullcontext():
            users = get_user_model().objects
            if business:
                user = users.filter(email__iexact=identifier).first()
            else:
                user = users.filter(username=identifier).first()
            if user is None:
                where = f"en «{business.nombre}»" if business else "en el panel"
                raise CommandError(f"No hay ningún usuario «{identifier}» {where}.")
            unlocked = unlock(user, REASON)
        if unlocked:
            self.stdout.write(self.style.SUCCESS(f"«{identifier}» quedó desbloqueado."))
        else:
            self.stdout.write(f"«{identifier}» no estaba bloqueado: no hubo cambios.")

    def find_business(self, value):
        schema = value.strip().lower().replace("-", "_")
        business = Negocio.objects.exclude(schema_name=get_public_schema_name()).filter(schema_name=schema).first()
        if business is None:
            raise CommandError(f"No hay ningún negocio «{value}».")
        return business
