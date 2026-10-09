from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import schema_exists

from apps.tenancy.entorno_local import ESQUEMA_DEMO, exigir_debug
from apps.tenancy.models import Negocio, Persona, Rubro
from apps.tenancy.plataforma import asegurar_dominio, asegurar_negocio_publico

DOMINIOS_PUBLICOS = ("localhost", "admin.localhost")
DOMINIO_DEMO = "demo.localhost"


class Command(BaseCommand):
    help = (
        "Solo en desarrollo: crea el negocio public (localhost y admin.localhost) y el negocio "
        "demo (demo.localhost) con su esquema. Se puede repetir sin duplicar nada."
    )

    def handle(self, *args, **options):
        exigir_debug()
        connection.set_schema_to_public()

        publico, creado = asegurar_negocio_publico()
        self.informar(publico, creado)
        for dominio in DOMINIOS_PUBLICOS:
            self.informar_dominio(dominio, asegurar_dominio(dominio, publico, es_principal=dominio == DOMINIOS_PUBLICOS[0]))

        demo = Negocio.objects.filter(schema_name=ESQUEMA_DEMO).first()
        creado = demo is None
        if creado:
            demo = Negocio.objects.create(
                schema_name=ESQUEMA_DEMO,
                nombre="Negocio Demo",
                titular=Persona.objects.create(nombres="Titular", apellidos="Demo"),
                rubro=Rubro.objects.filter(codigo="unas").first(),
                estado=Negocio.Estado.ACTIVO,
            )
        self.informar(demo, creado)
        if not schema_exists(ESQUEMA_DEMO):
            demo.create_schema(check_if_exists=True, verbosity=options["verbosity"])
            self.stdout.write(f"  esquema «{ESQUEMA_DEMO}» creado y migrado")
        self.informar_dominio(DOMINIO_DEMO, asegurar_dominio(DOMINIO_DEMO, demo, es_principal=True))

    def informar(self, negocio, creado):
        estado = "creado" if creado else "ya existía"
        self.stdout.write(f"Negocio «{negocio.nombre}» ({negocio.schema_name}): {estado}")

    def informar_dominio(self, dominio, resultado):
        self.stdout.write(f"  dominio {dominio}: {resultado}")
