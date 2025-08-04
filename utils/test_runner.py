"""
TestRunner personalizado que usa una base de datos existente para tests
en lugar de crear una temporal.
"""

import os
from django.test.runner import DiscoverRunner
from django.db import connections
from django.conf import settings


class ExistingDatabaseTestRunner(DiscoverRunner):
    """
    TestRunner que usa la base de datos test_manicuredb existente
    y la limpia al inicio de cada ejecución de tests.
    """

    def setup_databases(self, **kwargs):
        """
        Configurar las bases de datos para tests.
        No crear nuevas bases de datos, usar la existente.
        """
        # Limpiar la base de datos de test al inicio
        self.clean_test_database()

        # Retornar configuración de la base de datos de test
        return [("test_db", True)]

    def teardown_databases(self, old_config, **kwargs):
        """
        Limpiar después de los tests.
        No destruir la base de datos, solo limpiar datos.
        """
        self.clean_test_database()

    def clean_test_database(self):
        """
        Limpiar todos los datos de la base de datos de test
        manteniendo la estructura (tablas, índices, etc.).
        """
        connection = connections["test_db"]
        cursor = connection.cursor()

        try:
            print("Limpiando base de datos de test...")

            # Obtener todas las tablas del proyecto (excluyendo las de Django admin)
            app_tables = [
                "clientes",
                "servicios",
                "citas",
                "detalle_cita",
                "pagos",
                "configuracion_salon",
            ]

            # Deshabilitar restricciones de clave foránea temporalmente
            cursor.execute("SET session_replication_role = replica;")

            # Truncar todas las tablas de la aplicación
            for table in app_tables:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                    print(f"  - Tabla {table} limpiada")
                except Exception as e:
                    print(f"  - Advertencia: No se pudo limpiar tabla {table}: {e}")

            # Rehabilitar restricciones de clave foránea
            cursor.execute("SET session_replication_role = DEFAULT;")

            connection.commit()
            print("Base de datos de test limpiada exitosamente.")

        except Exception as e:
            print(f"Error al limpiar base de datos de test: {e}")
            connection.rollback()
        finally:
            cursor.close()

    def setup_test_environment(self, **kwargs):
        """Configurar el entorno de test."""
        super().setup_test_environment(**kwargs)

        # Asegurar que estamos usando el router de test
        os.environ["DJANGO_TEST_MODE"] = "1"

        # Configurar variable para indicar que estamos en modo test
        settings.TESTING = True

    def teardown_test_environment(self, **kwargs):
        """Limpiar el entorno de test."""
        super().teardown_test_environment(**kwargs)

        # Limpiar variables de entorno
        if "DJANGO_TEST_MODE" in os.environ:
            del os.environ["DJANGO_TEST_MODE"]

        if hasattr(settings, "TESTING"):
            delattr(settings, "TESTING")
