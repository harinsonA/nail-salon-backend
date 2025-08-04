"""
Router de base de datos personalizado para dirigir operaciones de test
a la base de datos test_manicuredb existente.
"""

import os
import sys


class TestDatabaseRouter:
    """
    Router que dirige todas las operaciones de base de datos a test_manicuredb
    cuando se están ejecutando tests.
    """

    def _is_test_mode(self):
        """Detectar si estamos en modo test."""
        return (
            "test" in sys.argv
            or os.environ.get("DJANGO_TEST_MODE") == "1"
            or hasattr(sys.modules.get("django.conf", None), "settings")
            and getattr(sys.modules["django.conf"].settings, "TESTING", False)
        )

    def db_for_read(self, model, **hints):
        """Sugerir la base de datos de lectura para el modelo."""
        if self._is_test_mode():
            return "test_db"
        return None

    def db_for_write(self, model, **hints):
        """Sugerir la base de datos de escritura para el modelo."""
        if self._is_test_mode():
            return "test_db"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Permitir relaciones entre objetos del mismo proyecto."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Permitir migraciones."""
        # Durante tests, permitir migraciones solo en test_db
        if self._is_test_mode():
            return db == "test_db"
        # Durante desarrollo/producción, usar default
        return db == "default"
