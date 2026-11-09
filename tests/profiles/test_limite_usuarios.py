from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.seguridad.models import AccesoUsuario
from apps.tenancy.models import Negocio
from apps.tenancy.user_limit.messages import OVER_LIMIT_LOGIN, TEAM_DISABLED
from tests.base import IDENTIFICADOR_VALIDO, NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol

CLAVE = "Clave-Segura-123"
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class LimiteDeUsuariosEnElNegocioTests(NegocioTestCase):
    esquema = "limite_negocio"
    dominio = "limite-negocio.localhost"

    def setUp(self):
        super().setUp()
        self.maria = self.crear(Rol.PROPIETARIO, "maria")
        self.ana = self.crear(Rol.ENCARGADO, "ana")
        self.laura = self.crear(Rol.COLABORADOR, "laura")

    def crear(self, rol, nombre):
        usuario = User.objects.create_user(
            username=nombre, email=f"{nombre}@correo.cl", password=CLAVE
        )
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.select_related("perfil").get(pk=usuario.pk)

    def limite(self, valor):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=valor)

    def desactivar(self, *usuarios):
        User.objects.filter(pk__in=[usuario.pk for usuario in usuarios]).update(is_active=False)

    def navegador_de(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def entrar(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        respuesta = navegador.post(
            reverse("login"), {"username": usuario.email, "password": CLAVE}
        )
        return navegador, respuesta

    def lista(self, navegador):
        return navegador.get(reverse("equipo_lista"), **AJAX).json()

    def crear_miembro(self, navegador, correo="sofi@correo.cl"):
        return navegador.post(
            reverse("equipo_crear"),
            {**IDENTIFICADOR_VALIDO, "first_name": "Sofi", "email": correo, "rol": Rol.COLABORADOR},
        )

    def test_sin_limite_todo_sigue_como_hoy(self):
        navegador = self.navegador_de(self.maria)
        self.assertContains(navegador.get(reverse("calendar")), f'href="{reverse("equipo")}"')
        datos = self.lista(navegador)
        self.assertEqual(
            (datos["seat_counter"], datos["has_free_seat"]),
            ("3 cuentas activas · sin límite", True),
        )
        self.assertEqual(navegador.get(reverse("equipo_crear")).status_code, 200)
        self.assertEqual(self.crear_miembro(navegador).status_code, 200)

    def test_limite_uno_con_solo_la_propietaria_no_tiene_equipo(self):
        self.desactivar(self.ana, self.laura)
        self.limite(1)
        navegador = self.navegador_de(self.maria)
        calendario = navegador.get(reverse("calendar"))
        self.assertEqual(calendario.status_code, 200)
        self.assertNotContains(calendario, f'href="{reverse("equipo")}"')
        self.assertRedirects(
            navegador.get(reverse("equipo")), reverse("calendar"), fetch_redirect_response=False
        )
        respuesta = navegador.get(reverse("equipo_lista"), **AJAX)
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(
            respuesta.json(), {"message": TEAM_DISABLED, "redirect": reverse("calendar")}
        )
        self.assertRedirects(
            navegador.post(reverse("equipo_activar", args=[self.ana.pk])),
            reverse("calendar"),
            fetch_redirect_response=False,
        )
        self.assertFalse(User.objects.get(pk=self.ana.pk).is_active)

    def test_la_colaboradora_sigue_sin_ver_equipo(self):
        respuesta = self.navegador_de(self.laura).get(reverse("equipo"))
        self.assertEqual(respuesta.status_code, 403)

    def test_cupo_lleno_no_deja_crear(self):
        self.limite(3)
        navegador = self.navegador_de(self.maria)
        datos = self.lista(navegador)
        self.assertEqual(
            (datos["seat_counter"], datos["has_free_seat"]),
            ("3 de 3 cuentas activas", False),
        )
        self.assertIn("Llegaste al límite de 3 cuentas activas", datos["seat_refusal"])
        pagina = navegador.get(reverse("equipo"))
        self.assertContains(pagina, "3 de 3 cuentas activas")
        self.assertContains(pagina, "Llegaste al límite de 3 cuentas activas")
        self.assertEqual(navegador.get(reverse("equipo_crear")).status_code, 403)
        respuesta = self.crear_miembro(navegador)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Llegaste al límite de 3 cuentas activas", respuesta.json()["message"])
        self.assertFalse(User.objects.filter(email="sofi@correo.cl").exists())

    def test_con_cupo_crea_y_el_contador_sube(self):
        self.limite(4)
        navegador = self.navegador_de(self.maria)
        self.assertEqual(self.lista(navegador)["seat_counter"], "3 de 4 cuentas activas")
        self.assertEqual(self.crear_miembro(navegador).status_code, 200)
        datos = self.lista(navegador)
        self.assertEqual(
            (datos["seat_counter"], datos["has_free_seat"]),
            ("4 de 4 cuentas activas", False),
        )

    def test_reactivar_necesita_cupo_y_desactivar_siempre_se_puede(self):
        self.desactivar(self.laura)
        self.limite(2)
        navegador = self.navegador_de(self.maria)
        modal = navegador.get(reverse("equipo_activar", args=[self.laura.pk]), **AJAX)
        self.assertContains(modal, "Llegaste al límite de 2 cuentas activas")
        self.assertNotContains(modal, "member_active_submit_btn")
        respuesta = navegador.post(reverse("equipo_activar", args=[self.laura.pk]), **AJAX)
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(User.objects.get(pk=self.laura.pk).is_active)
        self.assertEqual(
            navegador.post(reverse("equipo_activar", args=[self.ana.pk]), **AJAX).status_code, 200
        )
        self.assertEqual(
            navegador.post(reverse("equipo_activar", args=[self.laura.pk]), **AJAX).status_code, 200
        )
        self.assertTrue(User.objects.get(pk=self.laura.pk).is_active)

    def test_por_encima_del_limite_solo_entra_la_propietaria(self):
        self.limite(1)
        for usuario in (self.ana, self.laura):
            with self.subTest(usuario=usuario.username):
                _, respuesta = self.entrar(usuario)
                self.assertEqual(respuesta.status_code, 200)
                self.assertFalse(respuesta.wsgi_request.user.is_authenticated)
                self.assertContains(respuesta, OVER_LIMIT_LOGIN)
                acceso = AccesoUsuario.objects.filter(user=usuario).first()
                self.assertEqual(acceso.intentos_fallidos if acceso else 0, 0)
        _, respuesta = self.entrar(self.maria)
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)

    def test_la_clave_incorrecta_sigue_contando_como_intento(self):
        self.limite(1)
        navegador = Client(HTTP_HOST=self.dominio)
        respuesta = navegador.post(
            reverse("login"), {"username": self.ana.email, "password": "otra"}
        )
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")
        self.assertNotContains(respuesta, OVER_LIMIT_LOGIN)
        self.assertEqual(AccesoUsuario.objects.get(user=self.ana).intentos_fallidos, 1)

    def test_quien_estaba_dentro_sale_en_su_siguiente_clic(self):
        navegador = self.navegador_de(self.ana)
        self.assertEqual(navegador.get(reverse("calendar")).status_code, 200)
        self.limite(2)
        respuesta = navegador.get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith(reverse("login")))
        self.assertNotIn("_auth_user_id", navegador.session)
        self.assertContains(navegador.get(reverse("login")), OVER_LIMIT_LOGIN)
        propietaria = self.navegador_de(self.maria)
        self.assertEqual(propietaria.get(reverse("calendar")).status_code, 200)

    def test_una_peticion_ajax_tambien_sale(self):
        navegador = self.navegador_de(self.laura)
        self.limite(1)
        respuesta = navegador.post(reverse("session_ping"), **AJAX)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["message"], OVER_LIMIT_LOGIN)

    def test_por_encima_la_propietaria_ve_el_aviso_y_solo_desactiva(self):
        self.desactivar(self.laura)
        self.crear(Rol.COLABORADOR, "sofi")
        self.limite(1)
        navegador = self.navegador_de(self.maria)
        calendario = navegador.get(reverse("calendar"))
        self.assertContains(calendario, "su límite es 1")
        self.assertContains(calendario, "desactiva 2 cuentas")
        self.assertContains(calendario, f'href="{reverse("equipo")}"')
        filas = {fila["email"]: fila for fila in self.lista(navegador)["data"]}
        self.assertEqual(
            [opcion["label"] for opcion in filas[self.ana.email]["options"]], ["Desactivar"]
        )
        self.assertEqual(filas[self.laura.email]["options"], [])
        for nombre in ("equipo_editar", "equipo_restablecer_clave", "equipo_desbloquear"):
            with self.subTest(nombre=nombre):
                url = reverse(nombre, args=[self.ana.pk])
                self.assertEqual(navegador.get(url).status_code, 403)
                respuesta = navegador.post(url, **AJAX)
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("solo se puede desactivar: faltan 2 cuentas", respuesta.json()["message"])
        self.assertEqual(navegador.post(reverse("equipo_activar", args=[self.laura.pk]), **AJAX).status_code, 400)
        self.assertEqual(self.crear_miembro(navegador, "otra@correo.cl").status_code, 400)
        self.assertEqual(navegador.post(reverse("equipo_activar", args=[self.ana.pk]), **AJAX).status_code, 200)

    def test_al_volver_al_limite_todo_se_normaliza(self):
        self.limite(2)
        _, respuesta = self.entrar(self.ana)
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)
        self.desactivar(self.laura)
        _, respuesta = self.entrar(self.ana)
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)
        navegador = self.navegador_de(self.maria)
        self.assertNotContains(navegador.get(reverse("calendar")), "su límite es")
        self.assertEqual(navegador.get(reverse("equipo_editar", args=[self.ana.pk]), **AJAX).status_code, 200)

    def test_al_bajar_a_uno_la_propietaria_sola_pierde_equipo(self):
        self.limite(1)
        navegador = self.navegador_de(self.maria)
        self.assertEqual(navegador.get(reverse("equipo")).status_code, 200)
        navegador.post(reverse("equipo_activar", args=[self.ana.pk]), **AJAX)
        navegador.post(reverse("equipo_activar", args=[self.laura.pk]), **AJAX)
        self.assertRedirects(
            navegador.get(reverse("equipo")), reverse("calendar"), fetch_redirect_response=False
        )
