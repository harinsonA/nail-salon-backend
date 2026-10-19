from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django_tenants.utils import schema_context

from apps.seguridad.access import lock_status, register_failure
from tests.base import NegocioTestCase

User = get_user_model()


def bloquear(usuario):
    for _ in range(5):
        register_failure(usuario)
    assert lock_status(usuario).is_locked


class ComandoDesbloquearUsuarioTests(NegocioTestCase):
    esquema = "comando"

    def setUp(self):
        super().setUp()
        self.miembro = User.objects.create_user(username="ana", email="ana@correo.cl")
        connection.set_schema_to_public()
        self.admin = User.objects.create_user(username="admin_prueba", email="ana@correo.cl")

    def correr(self, *args):
        salida = StringIO()
        call_command("desbloquear_usuario", *args, stdout=salida)
        return salida.getvalue()

    def test_desbloquea_a_un_usuario_del_panel(self):
        bloquear(self.admin)
        salida = self.correr("admin_prueba")
        self.assertIn("quedó desbloqueado", salida)
        self.assertFalse(lock_status(self.admin).is_locked)

    def test_avisa_si_no_estaba_bloqueado(self):
        self.assertIn("no estaba bloqueado", self.correr("admin_prueba"))

    def test_desbloquea_en_un_negocio_por_correo(self):
        with schema_context(self.esquema):
            bloquear(self.miembro)
        bloquear(self.admin)
        salida = self.correr("ANA@correo.cl", "--negocio", self.esquema)
        self.assertIn("quedó desbloqueado", salida)
        with schema_context(self.esquema):
            self.assertFalse(lock_status(self.miembro).is_locked)
        self.assertTrue(lock_status(self.admin).is_locked)

    def test_el_negocio_no_distingue_mayusculas(self):
        with schema_context(self.esquema):
            bloquear(self.miembro)
        self.assertIn("quedó desbloqueado", self.correr("ana@correo.cl", "--negocio", self.esquema.upper()))

    def test_usuario_inexistente(self):
        with self.assertRaisesMessage(CommandError, "No hay ningún usuario «nadie» en el panel."):
            self.correr("nadie")
        with self.assertRaisesMessage(CommandError, "No hay ningún usuario «nadie@correo.cl» en «Negocio comando»."):
            self.correr("nadie@correo.cl", "--negocio", self.esquema)

    def test_negocio_inexistente(self):
        with self.assertRaisesMessage(CommandError, "No hay ningún negocio «otro»."):
            self.correr("ana@correo.cl", "--negocio", "otro")
