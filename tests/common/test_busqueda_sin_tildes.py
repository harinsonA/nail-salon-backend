from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.clients.models import Cliente
from apps.common.utils.search import without_accents
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()


class BusquedaSinTildesTests(NegocioTestCase):
    esquema = "busqueda_tildes"
    dominio = "busqueda-tildes.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)
        categoria = Categoria.objects.create(nombre="Uñas")
        Servicio.objects.create(nombre="Acrílico", precio=Decimal("15000"), categoria=categoria)
        Servicio.objects.create(nombre="Esmaltado", precio=Decimal("8000"), categoria=categoria)
        Cliente.objects.create(nombre="Verónica", apellido="Saavedra")
        Cliente.objects.create(nombre="Veronica", apellido="Jara")
        Cliente.objects.create(nombre="Paula", apellido="Peña")

    def buscar(self, url_name, texto, columna):
        respuesta = self.navegador.get(
            reverse(url_name),
            {"draw": 1, "start": 0, "length": 10, "order[0][column]": "0", "order[0][dir]": "asc", "search[value]": texto},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        return sorted(fila[columna] for fila in respuesta.json()["data"])

    def test_servicios_sin_tilde_encuentra_el_nombre_con_tilde(self):
        self.assertEqual(self.buscar("service_list", "acrilico", "nombre"), ["Acrílico"])

    def test_servicios_siguen_buscando_por_columnas_que_no_son_texto(self):
        self.assertEqual(self.buscar("service_list", "15000", "nombre"), ["Acrílico"])

    def test_clientes_con_o_sin_tilde_encuentra_las_dos(self):
        self.assertEqual(self.buscar("client_list", "veronica", "full_name"), ["Veronica Jara", "Verónica Saavedra"])
        self.assertEqual(self.buscar("client_list", "Verónica", "full_name"), ["Veronica Jara", "Verónica Saavedra"])

    def test_la_enie_sigue_siendo_distinta_de_la_ene(self):
        self.assertEqual(self.buscar("client_list", "Pena", "full_name"), [])
        self.assertEqual(self.buscar("client_list", "Peña", "full_name"), ["Paula Peña"])

    def test_quita_las_tildes_del_texto(self):
        self.assertEqual(without_accents("Árbol Pingüino Ñandú"), "Arbol Pinguino Ñandu")
