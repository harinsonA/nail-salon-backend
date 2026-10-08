import re

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.profiles.permisos import puede_gestionar
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class EquipoTests(NegocioTestCase):
    esquema = "equipo"
    dominio = "equipo.localhost"

    def crear(self, rol, nombre=None):
        nombre = nombre or rol
        usuario = User.objects.create_user(username=nombre, email=f"{nombre}@correo.cl", password="x")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.select_related("perfil").get(pk=usuario.pk)

    def navegador_de(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def clave_en(self, respuesta):
        return re.search(r"<code[^>]*>([a-z2-9-]{14})</code>", respuesta.content.decode()).group(1)

    def test_quien_gestiona_a_quien(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        encargada = self.crear(Rol.ENCARGADO, "ana")
        otra_encargada = self.crear(Rol.ENCARGADO, "sofi")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        self.assertTrue(puede_gestionar(propietaria, encargada))
        self.assertTrue(puede_gestionar(propietaria, colaboradora))
        self.assertTrue(puede_gestionar(encargada, colaboradora))
        self.assertFalse(puede_gestionar(encargada, otra_encargada))
        self.assertFalse(puede_gestionar(encargada, propietaria))
        self.assertFalse(puede_gestionar(propietaria, propietaria))
        self.assertFalse(puede_gestionar(colaboradora, colaboradora))

    def test_la_lista_muestra_acciones_solo_sobre_quien_se_puede_gestionar(self):
        encargada = self.crear(Rol.ENCARGADO, "ana")
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        lista = self.navegador_de(encargada).get(reverse("equipo"))
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, reverse("equipo_activar", args=[colaboradora.pk]))
        self.assertNotContains(lista, reverse("equipo_activar", args=[propietaria.pk]))
        self.assertNotContains(lista, reverse("equipo_activar", args=[encargada.pk]))

    def test_la_propietaria_crea_un_encargado_con_clave_temporal(self):
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        respuesta = navegador.post(
            reverse("equipo_crear"),
            {"first_name": "Ana", "last_name": "Pérez", "email": "Ana@Correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("no-store", respuesta["Cache-Control"])
        nueva = User.objects.get(email="ana@correo.cl")
        self.assertEqual(nueva.perfil.rol, Rol.ENCARGADO)
        self.assertTrue(nueva.perfil.debe_cambiar_clave)
        self.assertTrue(nueva.check_password(self.clave_en(respuesta)))

    def test_la_encargada_solo_crea_colaboradores(self):
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        formulario = navegador.get(reverse("equipo_crear"))
        self.assertEqual([valor for valor, _ in formulario.context["form"].fields["rol"].choices], [Rol.COLABORADOR])
        intento = navegador.post(
            reverse("equipo_crear"),
            {"first_name": "Sofi", "email": "sofi@correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertIn("rol", intento.context["form"].errors)
        self.assertFalse(User.objects.filter(email="sofi@correo.cl").exists())

    def test_no_se_repite_un_correo(self):
        self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        respuesta = navegador.post(
            reverse("equipo_crear"),
            {"first_name": "Laura", "email": "LAURA@correo.cl", "rol": Rol.COLABORADOR},
        )
        self.assertIn("email", respuesta.context["form"].errors)

    def test_desactivar_y_reactivar(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        self.assertRedirects(
            navegador.post(reverse("equipo_activar", args=[colaboradora.pk])),
            reverse("equipo"),
            fetch_redirect_response=False,
        )
        colaboradora.refresh_from_db()
        self.assertFalse(colaboradora.is_active)
        sesion_de_laura = self.navegador_de(colaboradora)
        self.assertRedirects(
            sesion_de_laura.get(reverse("calendar")), f"{reverse('login')}?next={reverse('calendar')}",
            fetch_redirect_response=False,
        )
        navegador.post(reverse("equipo_activar", args=[colaboradora.pk]))
        colaboradora.refresh_from_db()
        self.assertTrue(colaboradora.is_active)

    def test_restablecer_la_clave_de_un_colaborador(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        respuesta = self.navegador_de(self.crear(Rol.ENCARGADO, "ana")).post(
            reverse("equipo_restablecer_clave", args=[colaboradora.pk])
        )
        colaboradora.refresh_from_db()
        self.assertTrue(colaboradora.check_password(self.clave_en(respuesta)))
        self.assertTrue(colaboradora.perfil.debe_cambiar_clave)

    def test_nadie_del_negocio_toca_a_la_propietaria_ni_la_encargada_a_otra(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        otra_encargada = self.crear(Rol.ENCARGADO, "sofi")
        encargada = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        for objetivo in (propietaria, otra_encargada):
            for ruta in ("equipo_activar", "equipo_restablecer_clave"):
                with self.subTest(objetivo=objetivo.username, ruta=ruta):
                    self.assertEqual(encargada.post(reverse(ruta, args=[objetivo.pk])).status_code, 403)
        propia = self.navegador_de(propietaria)
        self.assertEqual(propia.post(reverse("equipo_activar", args=[propietaria.pk])).status_code, 403)
        propietaria.refresh_from_db()
        self.assertTrue(propietaria.is_active)
        self.assertTrue(propietaria.check_password("x"))

    def test_el_colaborador_no_entra_al_equipo(self):
        navegador = self.navegador_de(self.crear(Rol.COLABORADOR, "laura"))
        self.assertEqual(navegador.get(reverse("equipo")).status_code, 403)
        self.assertNotContains(navegador.get(reverse("calendar")), f'href="{reverse("equipo")}"')
