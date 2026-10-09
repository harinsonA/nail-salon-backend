from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()

CORREO = "maria@elcorte.cl"
CLAVE = "Clave-Temporal-123"
NUEVA = "Otra-Clave-Segura-456"


class AccesoConCorreoTests(NegocioTestCase):
    esquema = "acceso"
    dominio = "acceso.localhost"

    def crear_usuario(self, debe_cambiar_clave=False, **datos):
        usuario = User.objects.create_user(username="maria", email=CORREO, password=CLAVE, **datos)
        usuario.perfil.debe_cambiar_clave = debe_cambiar_clave
        usuario.perfil.save()
        return usuario

    def entrar(self, correo, clave=CLAVE):
        navegador = Client(HTTP_HOST=self.dominio)
        respuesta = navegador.post(reverse("login"), {"username": correo, "password": clave})
        return navegador, respuesta

    def test_entra_con_el_correo_sin_importar_mayusculas(self):
        self.crear_usuario()
        _, respuesta = self.entrar("  MARIA@ElCorte.cl ")
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)

    def test_no_entra_con_el_nombre_de_usuario(self):
        self.crear_usuario()
        _, respuesta = self.entrar("maria")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")

    def test_un_usuario_desactivado_no_entra(self):
        self.crear_usuario(is_active=False)
        _, respuesta = self.entrar(CORREO)
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)

    def test_con_clave_temporal_todo_lleva_a_cambiar_clave(self):
        self.crear_usuario(debe_cambiar_clave=True)
        navegador, _ = self.entrar(CORREO)
        self.assertRedirects(navegador.get(reverse("calendar")), reverse("cambiar_clave"), fetch_redirect_response=False)
        ajax = navegador.get(reverse("client_list"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(ajax.status_code, 403)
        self.assertEqual(ajax.json()["redirect"], reverse("cambiar_clave"))
        self.assertEqual(navegador.get(reverse("cambiar_clave")).status_code, 200)

    def test_cambiar_la_clave_libera_la_app(self):
        usuario = self.crear_usuario(debe_cambiar_clave=True)
        navegador, _ = self.entrar(CORREO)
        respuesta = navegador.post(reverse("cambiar_clave"), {"new_password1": NUEVA, "new_password2": NUEVA})
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)
        self.assertEqual(navegador.get(reverse("calendar")).status_code, 200)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(NUEVA))
        self.assertFalse(usuario.perfil.debe_cambiar_clave)

    def test_la_clave_nueva_pasa_los_validadores(self):
        usuario = self.crear_usuario(debe_cambiar_clave=True)
        navegador, _ = self.entrar(CORREO)
        respuesta = navegador.post(reverse("cambiar_clave"), {"new_password1": "123", "new_password2": "123"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        usuario.refresh_from_db()
        self.assertTrue(usuario.perfil.debe_cambiar_clave)

    def test_el_correo_se_guarda_en_minusculas(self):
        usuario = User.objects.create_user(username="ana", email="  Ana@Correo.CL ")
        usuario.refresh_from_db()
        self.assertEqual(usuario.email, "ana@correo.cl")

    def test_la_base_rechaza_un_correo_repetido(self):
        self.crear_usuario()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(username="otra", email="MARIA@elcorte.cl")])

    def test_los_usuarios_sin_correo_no_chocan(self):
        User.objects.create_user(username="uno")
        User.objects.create_user(username="dos")
        self.assertEqual(User.objects.filter(email="").count(), 2)

    def test_todo_usuario_nuevo_nace_colaborador(self):
        perfil = User.objects.create_user(username="ana", email="ana@correo.cl").perfil
        self.assertEqual(perfil.rol, Perfil.Rol.COLABORADOR)
        self.assertTrue(perfil.debe_cambiar_clave)


class AccesoPlataformaTests(TestCase):
    def test_la_plataforma_sigue_entrando_con_usuario(self):
        connection.set_schema_to_public()
        User.objects.create_user(username="admin", password=CLAVE)
        self.assertIsNotNone(authenticate(username="admin", password=CLAVE))
        self.assertIsNone(authenticate(username="admin", password="otra"))
