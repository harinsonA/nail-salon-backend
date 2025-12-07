"""
Custom User factories para generar datos de test.

Este módulo contiene factories para el modelo CustomUser.
"""

import factory
from factory.django import DjangoModelFactory
from apps.authentication.models import CustomUser
from utils.env_config import SystemUserConfig


class CustomUserFactory(DjangoModelFactory):
    """Factory para crear usuarios personalizados."""

    class Meta:
        model = CustomUser
        django_get_or_create = ("email",)

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = "salon_admin"  # Default role
    is_active = True
    is_staff = False

    @factory.PostGeneration
    def password(self, create, extracted, **kwargs):
        """Establecer password después de crear el usuario."""
        if not create:
            return

        # Usar password por defecto del .env si no se especifica otro
        test_config = SystemUserConfig.get_test_config()
        password = extracted or test_config["default_password"]
        self.set_password(password)
        self.save()


class AdminCustomUserFactory(CustomUserFactory):
    """Factory para crear usuarios super administradores."""

    username = factory.Sequence(lambda n: f"admin_test_{n}")
    email = factory.Sequence(lambda n: f"admin_test_{n}@test.com")
    role = "super_admin"
    is_staff = True


class EmployeeCustomUserFactory(CustomUserFactory):
    """Factory para crear usuarios salon admin (empleados del salón)."""

    username = factory.Sequence(lambda n: f"employee_test_{n}")
    email = factory.Sequence(lambda n: f"employee_test_{n}@test.com")
    role = "salon_admin"
    is_staff = False
