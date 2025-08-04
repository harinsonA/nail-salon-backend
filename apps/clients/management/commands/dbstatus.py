"""
Comando para verificar el estado de sincronización entre las bases de datos
principal y de test.
"""

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Verifica el estado de sincronización entre las bases de datos principal y de test"

    def add_arguments(self, parser):
        """Agregar argumentos del comando."""
        parser.add_argument(
            "--tables",
            action="store_true",
            help="Mostrar lista detallada de tablas en ambas bases.",
        )

    def handle(self, *args, **options):
        """Verificar estado de sincronización."""

        self.stdout.write(self.style.SUCCESS("=== Estado de Bases de Datos ===\n"))

        # 1. Verificar base principal
        main_status = self._check_database_status(
            "default", "Base Principal (manicuredb)"
        )

        # 2. Verificar base de test
        test_status = self._check_database_status(
            "test_db", "Base de Test (test_manicuredb)"
        )

        # 3. Comparar estados
        self._compare_databases(main_status, test_status)

        # 4. Mostrar tablas si se solicita
        if options.get("tables", False):
            self._show_tables_comparison()

    def _check_database_status(self, db_alias, db_name):
        """Verificar estado de una base de datos específica."""
        self.stdout.write(f"\n--- {db_name} ---")

        status = {
            "connected": False,
            "tables_count": 0,
            "tables": [],
            "pending_migrations": [],
            "applied_migrations": 0,
        }

        try:
            # Verificar conexión
            connection = connections[db_alias]
            connection.ensure_connection()
            status["connected"] = True
            self.stdout.write(f"✓ Conexión: {self.style.SUCCESS('OK')}")

            # Contar tablas
            cursor = connection.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            status["tables"] = [table[0] for table in tables]
            status["tables_count"] = len(tables)

            self.stdout.write(f"📊 Tablas: {status['tables_count']}")

            # Verificar migraciones
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            status["pending_migrations"] = plan
            status["applied_migrations"] = len(executor.loader.applied_migrations)

            if plan:
                self.stdout.write(
                    f"⚠ Migraciones pendientes: {self.style.WARNING(len(plan))}"
                )
                for migration, backwards in plan:
                    self.stdout.write(f"  - {migration}")
            else:
                self.stdout.write(f"✓ Migraciones: {self.style.SUCCESS('Al día')}")

        except Exception as e:
            status["connected"] = False
            self.stdout.write(f"❌ Error: {self.style.ERROR(str(e))}")

        return status

    def _compare_databases(self, main_status, test_status):
        """Comparar el estado entre ambas bases de datos."""
        self.stdout.write(self.style.SUCCESS("\n=== Comparación de Estados ==="))

        # Comparar conectividad
        if main_status["connected"] and test_status["connected"]:
            self.stdout.write("✓ Ambas bases de datos están conectadas")
        elif main_status["connected"]:
            self.stdout.write("⚠ Solo la base principal está disponible")
        elif test_status["connected"]:
            self.stdout.write("⚠ Solo la base de test está disponible")
        else:
            self.stdout.write("❌ Ninguna base de datos está disponible")
            return

        # Comparar número de tablas
        if main_status["tables_count"] == test_status["tables_count"]:
            self.stdout.write(
                f"✓ Número de tablas coincide: {main_status['tables_count']}"
            )
        else:
            self.stdout.write(
                f"⚠ Diferencia en tablas: Principal({main_status['tables_count']}) vs "
                f"Test({test_status['tables_count']})"
            )

        # Comparar migraciones pendientes
        main_pending = len(main_status["pending_migrations"])
        test_pending = len(test_status["pending_migrations"])

        if main_pending == 0 and test_pending == 0:
            self.stdout.write("✓ Ambas bases están al día con las migraciones")
        elif main_pending == test_pending:
            self.stdout.write(
                f"⚠ Ambas bases tienen {main_pending} migraciones pendientes"
            )
        else:
            self.stdout.write(
                f"❌ Migraciones desincronizadas: Principal({main_pending}) vs Test({test_pending})"
            )

        # Recomendaciones
        self._show_recommendations(main_status, test_status)

    def _show_recommendations(self, main_status, test_status):
        """Mostrar recomendaciones basadas en el estado."""
        self.stdout.write(self.style.SUCCESS("\n=== Recomendaciones ==="))

        main_pending = len(main_status["pending_migrations"])
        test_pending = len(test_status["pending_migrations"])

        if main_pending > 0 or test_pending > 0:
            self.stdout.write("🔧 Ejecuta: python manage.py migrate_all")
        elif main_status["tables_count"] != test_status["tables_count"]:
            self.stdout.write("🔧 Ejecuta: python manage.py sync_test_db")
        else:
            self.stdout.write("✅ Todo está sincronizado. No se requiere acción.")

    def _show_tables_comparison(self):
        """Mostrar comparación detallada de tablas."""
        self.stdout.write(self.style.SUCCESS("\n=== Comparación de Tablas ==="))

        try:
            # Obtener tablas de ambas bases
            main_connection = connections["default"]
            test_connection = connections["test_db"]

            # Tablas principales
            cursor = main_connection.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            main_tables = set(table[0] for table in cursor.fetchall())

            # Tablas de test
            cursor = test_connection.cursor()
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' ORDER BY table_name
            """)
            test_tables = set(table[0] for table in cursor.fetchall())

            # Comparar
            common_tables = main_tables & test_tables
            main_only = main_tables - test_tables
            test_only = test_tables - main_tables

            self.stdout.write(f"Tablas comunes: {len(common_tables)}")
            for table in sorted(common_tables):
                self.stdout.write(f"  ✓ {table}")

            if main_only:
                self.stdout.write(f"\nSolo en principal: {len(main_only)}")
                for table in sorted(main_only):
                    self.stdout.write(f"  ⚠ {table}")

            if test_only:
                self.stdout.write(f"\nSolo en test: {len(test_only)}")
                for table in sorted(test_only):
                    self.stdout.write(f"  ⚠ {table}")

        except Exception as e:
            self.stdout.write(f"Error al comparar tablas: {e}")
