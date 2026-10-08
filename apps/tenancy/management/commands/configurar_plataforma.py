from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.tenancy.plataforma import asegurar_dominio, asegurar_negocio_publico
from apps.tenancy.subdominios import SUBDOMINIO_PANEL


class Command(BaseCommand):
    help = (
        "Registra la plataforma (el negocio public) con sus dominios: el raíz de DOMINIO_BASE, www, el panel "
        "y el de Render. Se puede repetir: solo crea lo que falta."
    )

    def add_arguments(self, parser):
        parser.add_argument("--extra", nargs="*", default=[], help="Otros dominios que deben llevar a la plataforma.")

    def handle(self, *args, extra, **options):
        base = settings.DOMINIO_BASE
        if not settings.DEBUG and base in ("", "localhost"):
            raise CommandError("Define DOMINIO_BASE (por ejemplo, hi-agenda.com) antes de configurar la plataforma.")
        connection.set_schema_to_public()
        publico, creado = asegurar_negocio_publico()
        self.stdout.write(f"Plataforma «{publico.nombre}»: {'creada' if creado else 'ya existía'}")
        dominios = [base, f"www.{base}", f"{SUBDOMINIO_PANEL}.{base}", settings.RENDER_EXTERNAL_HOSTNAME, *extra]
        for dominio in dict.fromkeys(d for d in dominios if d):
            resultado = asegurar_dominio(dominio, publico, es_principal=dominio == base)
            self.stdout.write(f"  dominio {dominio}: {resultado}")
