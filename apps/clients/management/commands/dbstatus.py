"""
Comando para verificar el estado de la base de datos:
conectividad, tablas y migraciones pendientes.
"""

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Verifica conectividad, tablas y migraciones pendientes de la base de datos"

    def add_arguments(self, parser):
        """Agregar argumentos del comando."""
        parser.add_argument(
            "--tables",
            action="store_true",
            help="Mostrar lista detallada de tablas.",
        )

    def handle(self, *args, **options):
        """Verificar estado de la base de datos."""

        self.stdout.write(self.style.SUCCESS("=== Estado de la Base de Datos ===\n"))

        status = {
            "connected": False,
            "tables": [],
            "pending_migrations": [],
        }

        try:
            # Verificar conexión
            connection = connections["default"]
            connection.ensure_connection()
            status["connected"] = True
            db_name = connection.settings_dict.get("NAME", "")
            self.stdout.write(f"✓ Conexión a '{db_name}': {self.style.SUCCESS('OK')}")

            # Contar tablas
            cursor = connection.cursor()
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            status["tables"] = [table[0] for table in cursor.fetchall()]
            self.stdout.write(f"📊 Tablas: {len(status['tables'])}")

            # Verificar migraciones
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            status["pending_migrations"] = plan

            if plan:
                self.stdout.write(
                    f"⚠ Migraciones pendientes: {self.style.WARNING(len(plan))}"
                )
                for migration, backwards in plan:
                    self.stdout.write(f"  - {migration}")
                self.stdout.write("\n🔧 Ejecuta: python manage.py migrate")
            else:
                self.stdout.write(f"✓ Migraciones: {self.style.SUCCESS('Al día')}")

        except Exception as e:
            self.stdout.write(f"❌ Error: {self.style.ERROR(str(e))}")
            return

        # Mostrar tablas si se solicita
        if options.get("tables", False):
            self.stdout.write(self.style.SUCCESS("\n=== Tablas ==="))
            for table in status["tables"]:
                self.stdout.write(f"  ✓ {table}")
