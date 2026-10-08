from django.conf import settings
from django.db import connection
from django.test import TestCase

from apps.tenancy.models import Dominio, Negocio, Persona


def crear_negocio_de_prueba(esquema, dominio=None):
    connection.set_schema_to_public()
    titular = Persona.objects.create(nombres=f"Titular {esquema}")
    negocio = Negocio.objects.create(
        schema_name=esquema,
        nombre=f"Negocio {esquema}",
        titular=titular,
        estado=Negocio.Estado.ACTIVO,
    )
    negocio.create_schema(check_if_exists=True, verbosity=0)
    if dominio:
        Dominio.objects.create(domain=dominio, tenant=negocio, is_primary=True)
    return negocio


def borrar_negocio_de_prueba(negocio):
    connection.set_schema_to_public()
    titular = negocio.titular
    negocio.domains.all().delete()
    negocio.delete(force_drop=True)
    titular.delete(soft=False)


class NegocioTestCase(TestCase):
    esquema = "prueba"
    dominio = None

    @classmethod
    def setUpClass(cls):
        if cls.dominio:
            settings.ALLOWED_HOSTS += [cls.dominio]
        cls.negocio = crear_negocio_de_prueba(cls.esquema, dominio=cls.dominio)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        borrar_negocio_de_prueba(cls.negocio)
        if cls.dominio:
            settings.ALLOWED_HOSTS.remove(cls.dominio)

    def setUp(self):
        super().setUp()
        connection.set_tenant(self.negocio)

    def tearDown(self):
        connection.set_schema_to_public()
        super().tearDown()
