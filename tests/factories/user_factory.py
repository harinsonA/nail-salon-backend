"""
User factories para generar datos de test.

Este módulo contiene factories para el modelo User personalizado.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory para crear usuarios personalizados."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = "salon_admin"  # Valor por defecto
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.PostGeneration
    def password(self, create, extracted, **kwargs):
        """Establecer password después de crear el usuario."""
        if not create:
            return

        password = extracted or "testpassword123"
        self.set_password(password)
        self.save()


class AdminUserFactory(UserFactory):
    """Factory para crear usuarios administradores."""

    username = "admin_test"
    email = "admin@test.com"
    role = "super_admin"
    is_staff = True
    is_superuser = True
