from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context, schema_exists

from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences.constants import Scope
from apps.tenancy.entorno_local import (
    COLUMNAS_RENOMBRADAS,
    ESQUEMA_DEMO,
    ESQUEMA_LEGADO,
    TABLAS_RENOMBRADAS,
    columnas_de,
    exigir_debug,
    nombre_calificado,
    tablas_del_esquema,
)
from apps.tenancy.models import Negocio

NO_SE_COPIAN = {
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "auth_group_permissions",
    "auth_user_user_permissions",
    "django_admin_log",
    "django_session",
}
COMPARTIDAS = {"auth_user", "auth_group", "auth_user_groups"}


class Command(BaseCommand):
    help = (
        "Solo en desarrollo: vacía el esquema de un negocio y copia en él los datos de otro esquema "
        "(por defecto, de «legado» a «demo»). Se puede repetir: cada vez parte de cero."
    )

    def add_arguments(self, parser):
        parser.add_argument("--desde", default=ESQUEMA_LEGADO, help="Esquema de origen.")
        parser.add_argument("--hacia", default=ESQUEMA_DEMO, help="Esquema del negocio de destino.")

    def handle(self, *args, desde, hacia, **options):
        exigir_debug()
        connection.set_schema_to_public()
        if not schema_exists(desde):
            raise CommandError(f"No existe el esquema de origen «{desde}».")
        if hacia == get_public_schema_name() or not Negocio.objects.filter(schema_name=hacia).exists():
            raise CommandError(f"«{hacia}» no es un negocio.")

        copias = self.planificar(desde, hacia)
        with transaction.atomic():
            self.vaciar(hacia, copias)
            for tabla, esquema_origen, tabla_origen in copias:
                filas = self.copiar(esquema_origen, tabla_origen, hacia, tabla)
                self.stdout.write(f"  {tabla}: {filas}")
            with schema_context(hacia):
                self.reiniciar_secuencias(copias)
                Preference.objects.filter(scope="salon").update(scope=Scope.NEGOCIO)
                Preference.history.model.objects.filter(scope="salon").update(scope=Scope.NEGOCIO)
                self.asignar_perfiles()
        self.stdout.write(self.style.SUCCESS(f"Datos copiados de «{desde}» a «{hacia}»."))

    def planificar(self, desde, hacia):
        en_origen = tablas_del_esquema(desde)
        en_publico = tablas_del_esquema(get_public_schema_name())
        nombres_anteriores = {nuevo: anterior for anterior, nuevo in TABLAS_RENOMBRADAS.items()}
        copias = []
        for tabla in sorted(tablas_del_esquema(hacia) - NO_SE_COPIAN):
            for candidata in (tabla, nombres_anteriores.get(tabla)):
                if candidata in en_origen:
                    copias.append((tabla, desde, candidata))
                    break
            else:
                if tabla in COMPARTIDAS and tabla in en_publico:
                    copias.append((tabla, get_public_schema_name(), tabla))
        return copias

    def vaciar(self, hacia, copias):
        tablas = ", ".join(nombre_calificado(hacia, tabla) for tabla, _, _ in copias)
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE")
            cursor.execute("SET CONSTRAINTS ALL DEFERRED")

    def copiar(self, esquema_origen, tabla_origen, esquema_destino, tabla_destino):
        renombres = COLUMNAS_RENOMBRADAS.get(tabla_destino, {})
        destino = set(columnas_de(esquema_destino, tabla_destino))
        pares = [
            (columna, renombres.get(columna, columna))
            for columna in columnas_de(esquema_origen, tabla_origen)
            if renombres.get(columna, columna) in destino
        ]
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {nombre_calificado(esquema_destino, tabla_destino)} "
                f"({', '.join(quote(nueva) for _, nueva in pares)}) "
                f"SELECT {', '.join(quote(original) for original, _ in pares)} "
                f"FROM {nombre_calificado(esquema_origen, tabla_origen)}"
            )
            return cursor.rowcount

    def reiniciar_secuencias(self, copias):
        tablas = {tabla for tabla, _, _ in copias}
        modelos = [modelo for modelo in apps.get_models(include_auto_created=True) if modelo._meta.db_table in tablas]
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), modelos):
                cursor.execute(sql)

    def asignar_perfiles(self):
        usuarios = get_user_model().objects.order_by("id")
        hay_propietario = Perfil.objects.filter(rol=Perfil.Rol.PROPIETARIO).exists()
        propietario = None
        if not hay_propietario:
            propietario = usuarios.filter(is_superuser=True, is_active=True).first() or usuarios.first()
        for usuario in usuarios.filter(perfil__isnull=True):
            rol = Perfil.Rol.PROPIETARIO if usuario == propietario else Perfil.Rol.COLABORADOR
            Perfil.objects.create(user=usuario, rol=rol, debe_cambiar_clave=False)
            self.stdout.write(f"  perfil de {usuario.username}: {rol}")
