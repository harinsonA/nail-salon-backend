"""
Comando para sincronizar la base de datos de test con la base principal.
Útil cuando se trabaja en equipo y se necesita actualizar la base de test.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.db import connections
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Command(BaseCommand):
    help = "Sincroniza la base de datos de test con la estructura actual del proyecto"

    def add_arguments(self, parser):
        """Agregar argumentos del comando."""
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Recrear completamente la base de datos de test (elimina y crea nueva).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forzar sincronización sin confirmación.",
        )

    def handle(self, *args, **options):
        """Sincronizar base de datos de test."""

        # Verificar configuración
        if "test_db" not in settings.DATABASES:
            self.stdout.write(
                self.style.ERROR(
                    "Error: Base de datos de test no configurada en settings.py"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("=== Sincronización de Base de Datos de Test ===")
        )

        # Confirmar acción si no es forzada
        if not options.get("force", False):
            if options.get("recreate", False):
                confirmation = input(
                    "\n⚠ ADVERTENCIA: Esto eliminará COMPLETAMENTE la base test_manicuredb "
                    'y todos sus datos.\n¿Estás seguro? (escribe "si" para continuar): '
                )
            else:
                confirmation = input(
                    "\n¿Aplicar migraciones a la base de datos de test? "
                    "(esto puede sobrescribir datos) (s/n): "
                )

            if confirmation.lower() not in ["s", "si", "y", "yes"]:
                self.stdout.write(self.style.WARNING("Operación cancelada."))
                return

        try:
            if options.get("recreate", False):
                # Recrear base de datos completamente
                self._recreate_test_database()
            else:
                # Solo aplicar migraciones
                self._migrate_test_database()

            self.stdout.write(
                self.style.SUCCESS("\n✓ Sincronización completada exitosamente")
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "La base de datos de test está actualizada y lista para usar."
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\nError durante la sincronización: {e}")
            )

    def _recreate_test_database(self):
        """Recrear completamente la base de datos de test."""
        self.stdout.write("1. Eliminando base de datos de test existente...")

        # Configuración de conexión
        db_config = settings.DATABASES["default"]

        # Conectar como admin para eliminar/crear base
        connection = psycopg2.connect(
            host=db_config["HOST"],
            port=db_config["PORT"],
            user=db_config["USER"],
            password=db_config["PASSWORD"],
            database="postgres",
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()

        try:
            # Terminar conexiones activas a la base de test
            cursor.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = 'test_manicuredb' AND pid <> pg_backend_pid()
            """)

            # Eliminar base si existe
            cursor.execute("DROP DATABASE IF EXISTS test_manicuredb")
            self.stdout.write("   ✓ Base de datos eliminada")

            # Crear nueva base
            cursor.execute("CREATE DATABASE test_manicuredb")
            self.stdout.write("   ✓ Nueva base de datos creada")

        finally:
            cursor.close()
            connection.close()

        # Aplicar migraciones a la nueva base
        self.stdout.write("2. Aplicando migraciones...")
        self._migrate_test_database()

    def _migrate_test_database(self):
        """Aplicar migraciones a la base de datos de test."""
        try:
            # Verificar conectividad
            test_connection = connections["test_db"]
            test_connection.ensure_connection()

            # Aplicar migraciones
            call_command("migrate", database="test_db", verbosity=1)

            self.stdout.write("   ✓ Migraciones aplicadas")

        except Exception as e:
            raise Exception(f"Error al aplicar migraciones: {e}")

    def _check_test_db_status(self):
        """Verificar el estado de la base de datos de test."""
        try:
            test_connection = connections["test_db"]
            test_connection.ensure_connection()

            cursor = test_connection.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = cursor.fetchall()

            self.stdout.write(f"Base de test contiene {len(tables)} tablas")
            return True

        except Exception as e:
            self.stdout.write(f"No se puede conectar a base de test: {e}")
            return False
