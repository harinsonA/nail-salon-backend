"""
User factories para generar datos de test.

Este módulo contiene factories para el modelo User de Django.
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User


class UserFactory(DjangoModelFactory):
    """Factory para crear usuarios de Django."""

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
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
    is_staff = True
    is_superuser = True
