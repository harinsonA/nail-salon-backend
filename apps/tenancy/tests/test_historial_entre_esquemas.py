from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import schema_context
from simple_history.models import HistoricalRecords

from apps.common.historial import sin_autor_de_la_peticion
from apps.profiles.models import Perfil
from apps.tenancy.models import Negocio
from apps.tenancy.propietario import restablecer_clave_del_propietario
from apps.tenancy.tasks import preparar_negocio
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()


class HistorialEntreEsquemasTests(NegocioTestCase):
    esquema = "historial"

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()
        self.admin = User.objects.create_superuser(username="admin", password="x")
        HistoricalRecords.context.request = SimpleNamespace(user=self.admin)

    def tearDown(self):
        if hasattr(HistoricalRecords.context, "request"):
            del HistoricalRecords.context.request
        super().tearDown()

    def autores_del_historial_de_perfiles(self):
        with schema_context(self.esquema):
            return list(Perfil.history.values_list("history_user_id", flat=True))

    def test_preparar_un_negocio_dentro_de_una_peticion_del_panel(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        preparar_negocio(self.negocio.pk, "nuevo@correo.cl", None)
        self.assertEqual(Negocio.objects.get(pk=self.negocio.pk).estado, Negocio.Estado.ACTIVO)
        autores = self.autores_del_historial_de_perfiles()
        self.assertTrue(autores)
        self.assertEqual(set(autores), {None})

    def test_restablecer_la_clave_dentro_de_una_peticion_del_panel(self):
        with schema_context(self.esquema), sin_autor_de_la_peticion():
            propietario = User.objects.create_user(username="maria", email="maria@correo.cl")
            Perfil.objects.filter(user=propietario).update(rol=Perfil.Rol.PROPIETARIO)
        restablecer_clave_del_propietario(Negocio.objects.get(pk=self.negocio.pk), self.admin)
        self.assertEqual(set(self.autores_del_historial_de_perfiles()), {None})
        self.assertEqual(Negocio.objects.get(pk=self.negocio.pk).history.first().history_user, self.admin)

    def test_la_peticion_vuelve_a_su_lugar_al_salir(self):
        with sin_autor_de_la_peticion():
            self.assertFalse(hasattr(HistoricalRecords.context, "request"))
        self.assertEqual(HistoricalRecords.context.request.user, self.admin)
