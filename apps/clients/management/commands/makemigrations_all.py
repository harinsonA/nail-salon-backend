"""
Comando personalizado que extiende 'makemigrations' y luego ejecuta 'migrate_all'
para mantener ambas bases de datos sincronizadas automáticamente.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Crea migraciones y las aplica automáticamente en ambas bases de datos"

    def add_arguments(self, parser):
        """Agregar argumentos del comando makemigrations original."""
        parser.add_argument(
            "args",
            metavar="app_label",
            nargs="*",
            help="Specify the app label(s) to create migrations for.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Just show what migrations would be made; don't actually write them.",
        )
        parser.add_argument(
            "--merge", action="store_true", help="Enable fixing of migration conflicts."
        )
        parser.add_argument(
            "--empty", action="store_true", help="Create an empty migration."
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with a non-zero status if model changes are missing migrations.",
        )
        parser.add_argument("--name", help="Use this name for migration file(s).")
        parser.add_argument(
            "--no-header",
            action="store_true",
            help="Do not add header comments to new migration file(s).",
        )
        parser.add_argument(
            "--skip-auto-migrate",
            action="store_true",
            help="Solo crear migraciones, no aplicarlas automáticamente.",
        )

    def handle(self, *args, **options):
        """Crear migraciones y aplicarlas automáticamente."""

        # 1. Ejecutar makemigrations
        self.stdout.write(self.style.SUCCESS("=== Creando migraciones ==="))

        try:
            # Preparar argumentos para makemigrations
            makemigrations_options = {
                "dry_run": options.get("dry_run", False),
                "merge": options.get("merge", False),
                "empty": options.get("empty", False),
                "check": options.get("check", False),
                "name": options.get("name"),
                "no_header": options.get("no_header", False),
                "verbosity": options.get("verbosity", 1),
            }

            # Filtrar opciones None
            makemigrations_options = {
                k: v for k, v in makemigrations_options.items() if v is not None
            }

            call_command("makemigrations", *args, **makemigrations_options)

            self.stdout.write(self.style.SUCCESS("✓ Migraciones creadas exitosamente"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al crear migraciones: {e}"))
            return

        # 2. Aplicar migraciones automáticamente (si no es dry-run o check)
        if (
            not options.get("dry_run", False)
            and not options.get("check", False)
            and not options.get("skip_auto_migrate", False)
        ):
            self.stdout.write(
                self.style.SUCCESS("\n=== Aplicando migraciones automáticamente ===")
            )

            try:
                # Usar nuestro comando migrate_all personalizado
                call_command("migrate_all", verbosity=options.get("verbosity", 1))

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error al aplicar migraciones: {e}")
                )
                self.stdout.write(
                    self.style.WARNING(
                        "Las migraciones se crearon pero no se aplicaron. "
                        'Ejecuta "python manage.py migrate_all" manualmente.'
                    )
                )
                return

        elif options.get("dry_run", False):
            self.stdout.write(
                self.style.WARNING("\n⚠ Modo dry-run: No se aplicaron migraciones")
            )
        elif options.get("check", False):
            self.stdout.write(
                self.style.WARNING("\n⚠ Modo check: No se aplicaron migraciones")
            )
        elif options.get("skip_auto_migrate", False):
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠ Auto-migración omitida: Ejecuta "python manage.py migrate_all" cuando estés listo'
                )
            )

        # 3. Resumen final
        if (
            not options.get("dry_run", False)
            and not options.get("check", False)
            and not options.get("skip_auto_migrate", False)
        ):
            self.stdout.write(self.style.SUCCESS("\n=== Proceso Completado ==="))
            self.stdout.write("✓ Migraciones creadas")
            self.stdout.write("✓ Migraciones aplicadas en base principal")
            self.stdout.write("✓ Migraciones aplicadas en base de test")
            self.stdout.write(
                self.style.SUCCESS(
                    "\nTu proyecto y base de datos de test están completamente sincronizados."
                )
            )
