from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.profiles.models import Perfil
from apps.settings.preferences.registry import APP_MODULE
from apps.settings.preferences.service import set_preference
from tests.base import NegocioTestCase

User = get_user_model()


class ApiTestCase(NegocioTestCase):
    app_version = "1.0.0"

    def setUp(self):
        super().setUp()
        set_preference(APP_MODULE.key, True)
        self.api_client = APIClient(HTTP_HOST=self.dominio, HTTP_X_APP_VERSION=self.app_version)

    def make_user(self, rol, debe_cambiar_clave=False):
        user = User.objects.create_user(
            username=f"{rol}_api", email=f"{rol}.api@correo.cl", first_name="Ana", last_name="Rojas"
        )
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=debe_cambiar_clave)
        return User.objects.get(pk=user.pk)

    def log_in_as(self, rol, **kwargs):
        user = self.make_user(rol, **kwargs)
        self.api_client.force_authenticate(user)
        return user

    def assertApiError(self, response, status_code, code):
        self.assertEqual(response.status_code, status_code, response.content)
        self.assertEqual(response.json()["code"], code)
        self.assertTrue(response.json()["message"])
