from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()


class ConteoListasTests(NegocioTestCase):
    esquema = "conteo_listas"
    dominio = "conteo-listas.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)
        Cliente.objects.create(nombre="Verónica", apellido="Saavedra")
        Cliente.objects.create(nombre="Paula", apellido="Peña")
        Cliente.objects.create(nombre="Camila", apellido="Rojas")

    def listar(self, busqueda=""):
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.navegador.get(
                reverse("client_list"),
                {"draw": 1, "start": 0, "length": 10, "search[value]": busqueda},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
        self.assertEqual(respuesta.status_code, 200)
        conteos = [q for q in consultas.captured_queries if "COUNT(*)" in q["sql"]]
        return respuesta.json(), len(conteos)

    def test_sin_busqueda_cuenta_una_sola_vez(self):
        datos, conteos = self.listar()
        self.assertEqual(conteos, 1)
        self.assertEqual((datos["recordsTotal"], datos["recordsFiltered"]), (3, 3))
        self.assertEqual(len(datos["data"]), 3)

    def test_con_busqueda_cuenta_el_total_y_lo_filtrado(self):
        datos, conteos = self.listar("paula")
        self.assertEqual(conteos, 2)
        self.assertEqual((datos["recordsTotal"], datos["recordsFiltered"]), (3, 1))
        self.assertEqual(len(datos["data"]), 1)
