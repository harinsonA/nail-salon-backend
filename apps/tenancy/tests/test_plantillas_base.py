from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()


class BaseNegocioTests(NegocioTestCase):
    esquema = "base_negocio"
    dominio = "base-negocio.localhost"

    def setUp(self):
        super().setUp()
        usuario = User.objects.create_user(username="encargada", email="encargada@correo.cl")
        Perfil.objects.filter(user=usuario).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(usuario)

    def test_las_paginas_del_negocio_traen_sus_piezas(self):
        respuesta = self.navegador.get(reverse("clients"))
        self.assertContains(respuesta, f'data-login-url="{reverse("login")}"')
        self.assertContains(respuesta, f'data-session-ping-url="{reverse("session_ping")}"')
        self.assertContains(respuesta, f'action="{reverse("logout")}"')
        self.assertContains(respuesta, "menu__brand")
        self.assertContains(respuesta, 'id="session_expiry_modal"')
        self.assertContains(respuesta, 'id="profile_modal"')
        self.assertContains(respuesta, "initializeBSModals('#profile-modal-btn'")
