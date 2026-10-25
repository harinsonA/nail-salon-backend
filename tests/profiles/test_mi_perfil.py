import re

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol
PESTANA_PERSONAL = 'data-bs-target="#profile-personal"'


class MiPerfilTests(NegocioTestCase):
    esquema = "mi_perfil"
    dominio = "mi-perfil.localhost"

    def crear(self, rol, nombre):
        usuario = User.objects.create_user(
            username=nombre,
            email=f"{nombre}@correo.cl",
            password="clave-actual-1",
            first_name=nombre.title(),
            last_name="Rojas",
        )
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.select_related("perfil").get(pk=usuario.pk)

    def navegador_de(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def guardar(self, usuario, **cambios):
        datos = {
            "username": usuario.username,
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "email": usuario.email,
            "session_idle_minutes": "120",
            **cambios,
        }
        return self.navegador_de(usuario).post(
            reverse("profile_modal"), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def test_el_propietario_solo_ve_la_pestana_de_seguridad(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        html = (
            self.navegador_de(propietaria)
            .get(reverse("profile_modal"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            .content.decode()
        )
        self.assertNotIn(PESTANA_PERSONAL, html)
        self.assertNotIn("Información personal", html)
        for campo in ("username", "first_name", "last_name", "email"):
            with self.subTest(campo=campo):
                self.assertNotRegex(html, rf'<input[^>]*name="{campo}"')
        self.assertRegex(html, r'class="nav-link active" id="profile-security-tab"')
        self.assertRegex(html, r'class="tab-pane fade show active" id="profile-security"')
        self.assertIn('name="new_password"', html)

    def test_el_propietario_no_puede_cambiar_sus_datos_personales(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        respuesta = self.guardar(
            propietaria,
            username="otra",
            first_name="Otra",
            last_name="Persona",
            email="otra@correo.cl",
        )
        self.assertEqual(respuesta.status_code, 200)
        propietaria.refresh_from_db()
        self.assertEqual(
            (
                propietaria.username,
                propietaria.first_name,
                propietaria.last_name,
                propietaria.email,
            ),
            ("maria", "Maria", "Rojas", "maria@correo.cl"),
        )

    def test_el_propietario_si_puede_cambiar_su_contrasena(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        respuesta = self.guardar(
            propietaria,
            current_password="clave-actual-1",
            new_password="Clave-Nueva-2026",
            confirm_password="Clave-Nueva-2026",
        )
        self.assertEqual(respuesta.status_code, 200)
        propietaria.refresh_from_db()
        self.assertTrue(propietaria.check_password("Clave-Nueva-2026"))

    def test_encargado_y_colaborador_siguen_editando_sus_datos(self):
        for rol, nombre in ((Rol.ENCARGADO, "ana"), (Rol.COLABORADOR, "laura")):
            with self.subTest(rol=rol):
                usuario = self.crear(rol, nombre)
                html = (
                    self.navegador_de(usuario)
                    .get(reverse("profile_modal"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                    .content.decode()
                )
                self.assertIn(PESTANA_PERSONAL, html)
                self.assertNotRegex(html, r'<input[^>]*name="email"[^>]*disabled')
                respuesta = self.guardar(
                    usuario, first_name="Nueva", email=f"{nombre}.nueva@correo.cl"
                )
                self.assertEqual(respuesta.status_code, 200)
                usuario.refresh_from_db()
                self.assertEqual(
                    (usuario.first_name, usuario.email),
                    ("Nueva", f"{nombre}.nueva@correo.cl"),
                )
