"""
Archivo de configuración para ejecutar los tests.
"""

# Configuración para pytest
pytest_plugins = [
    "tests.fixtures",  # Si tenemos fixtures personalizados
]

# Configuración para Django
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nail_salon_api.settings")
django.setup()

# Configuración adicional para tests
TEST_CONFIG = {
    "USE_FACTORY_BOY": True,
    "CLEANUP_DATA": True,
    "VERBOSE_OUTPUT": True,
}
