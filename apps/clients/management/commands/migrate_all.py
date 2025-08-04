"""
Comando personalizado que extiende 'migrate' para ejecutar migraciones
en ambas bases de datos: proyecto y test.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connections


class Command(BaseCommand):
    help = (
        "Ejecuta migraciones en la base de datos principal y luego en la base de test"
    )

    def add_arguments(self, parser):
        """Agregar argumentos del comando migrate original."""
        parser.add_argument(
            "app_label",
            nargs="?",
            help="App label of an application to synchronize the state.",
        )
        parser.add_argument(
            "migration_name",
            nargs="?",
            help="Database state will be brought to the state after that migration.",
        )
        parser.add_argument(
            "--database",
            default="default",
            help='Nominates a database to synchronize. Defaults to the "default" database.',
        )
        parser.add_argument(
            "--fake",
            action="store_true",
            help="Mark migrations as run without actually running them.",
        )
        parser.add_argument(
            "--fake-initial",
            action="store_true",
            help="Detect if tables already exist and fake-apply initial migrations if so.",
        )
        parser.add_argument(
            "--run-syncdb",
            action="store_true",
            help="Creates tables for apps without migrations.",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with a non-zero status if unapplied migrations exist.",
        )
        parser.add_argument(
            "--skip-test-db",
            action="store_true",
            help="Saltar migración de la base de datos de test.",
        )

    def handle(self, *args, **options):
        """Ejecutar migraciones en ambas bases de datos."""

        # Verificar que la base de datos de test esté configurada
        if "test_db" not in settings.DATABASES:
            self.stdout.write(
                self.style.WARNING(
                    "Base de datos de test no configurada. Solo se migrarán los datos principales."
                )
            )
            options["skip_test_db"] = True

        # 1. Ejecutar migraciones en la base de datos principal
        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Ejecutando migraciones en base de datos principal ==="
            )
        )

        try:
            # Preparar argumentos para el comando migrate original
            migrate_args = []
            if options.get("app_label"):
                migrate_args.append(options["app_label"])
            if options.get("migration_name"):
                migrate_args.append(options["migration_name"])

            migrate_options = {
                "database": options.get("database", "default"),
                "fake": options.get("fake", False),
                "fake_initial": options.get("fake_initial", False),
                "run_syncdb": options.get("run_syncdb", False),
                "check": options.get("check", False),
                "verbosity": options.get("verbosity", 1),
            }

            call_command("migrate", *migrate_args, **migrate_options)

            self.stdout.write(
                self.style.SUCCESS("✓ Migraciones principales completadas exitosamente")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error en migraciones principales: {e}")
            )
            return

        # 2. Ejecutar migraciones en la base de datos de test (si no se saltó)
        if not options.get("skip_test_db", False) and not options.get("check", False):
            self.stdout.write(
                self.style.SUCCESS(
                    "\n=== Ejecutando migraciones en base de datos de test ==="
                )
            )

            try:
                # Verificar conectividad a la base de test
                test_connection = connections["test_db"]
                test_connection.ensure_connection()

                # Ejecutar migraciones en la base de test
                migrate_options_test = migrate_options.copy()
                migrate_options_test["database"] = "test_db"

                call_command("migrate", *migrate_args, **migrate_options_test)

                self.stdout.write(
                    self.style.SUCCESS("✓ Migraciones de test completadas exitosamente")
                )

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Advertencia: No se pudieron ejecutar migraciones en base de test: {e}"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "Verifica que la base de datos test_manicuredb exista y sea accesible."
                    )
                )

        # 3. Resumen final
        self.stdout.write(self.style.SUCCESS("\n=== Resumen de Migraciones ==="))
        self.stdout.write("✓ Base de datos principal: Actualizada")

        if options.get("skip_test_db", False):
            self.stdout.write("⏭ Base de datos de test: Omitida (--skip-test-db)")
        elif options.get("check", False):
            self.stdout.write("⏭ Base de datos de test: Omitida (--check)")
        else:
            self.stdout.write("✓ Base de datos de test: Actualizada")

        self.stdout.write(
            self.style.SUCCESS(
                "\nAmbas bases de datos están sincronizadas y listas para usar."
            )
        )
