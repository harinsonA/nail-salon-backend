from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.tenancy.entorno_local import ESQUEMA_DEMO, exigir_debug
from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

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

        publico, creado = Negocio.objects.get_or_create(
            schema_name=get_public_schema_name(),
            defaults={"nombre": "Hi Agenda", "estado": Negocio.Estado.ACTIVO},
        )
        self.informar(publico, creado)
        for dominio in DOMINIOS_PUBLICOS:
            self.asegurar_dominio(dominio, publico, es_principal=dominio == DOMINIOS_PUBLICOS[0])

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
        if demo.create_schema(check_if_exists=True, verbosity=options["verbosity"]):
            self.stdout.write(f"  esquema «{ESQUEMA_DEMO}» creado y migrado")
        self.asegurar_dominio(DOMINIO_DEMO, demo, es_principal=True)

    def informar(self, negocio, creado):
        estado = "creado" if creado else "ya existía"
        self.stdout.write(f"Negocio «{negocio.nombre}» ({negocio.schema_name}): {estado}")

    def asegurar_dominio(self, dominio, negocio, es_principal):
        existente = Dominio.objects.filter(domain=dominio).first()
        if existente is None:
            Dominio.objects.create(domain=dominio, tenant=negocio, is_primary=es_principal)
            self.stdout.write(f"  dominio {dominio}: creado")
        elif existente.tenant_id != negocio.pk:
            self.stdout.write(self.style.WARNING(f"  dominio {dominio}: ya apunta a otro negocio, no se cambió"))
        else:
            self.stdout.write(f"  dominio {dominio}: ya existía")
