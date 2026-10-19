from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from apps.seguridad.models import AccesoUsuario
from tests.base import NegocioTestCase

User = get_user_model()


def tablas_del_esquema():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


class AccesoUsuarioEnNegocioTests(NegocioTestCase):
    esquema = "seguridad"

    def setUp(self):
        super().setUp()
        self.usuario = User.objects.create_user(username="ana", email="ana@correo.cl")

    def test_las_tablas_existen_en_el_negocio(self):
        self.assertTrue({"accesos_usuario", "accesos_usuario_historial"} <= tablas_del_esquema())

    def test_no_se_crea_al_crear_el_usuario(self):
        self.assertFalse(AccesoUsuario.objects.filter(user=self.usuario).exists())

    def test_valores_por_defecto(self):
        acceso = AccesoUsuario.objects.create(user=self.usuario)
        acceso.refresh_from_db()
        self.assertEqual(acceso.intentos_fallidos, 0)
        self.assertIsNone(acceso.ultimo_intento_fallido)
        self.assertIsNone(acceso.bloqueado_hasta)
        self.assertFalse(acceso.bloqueado)
        self.assertIsNone(acceso.bloqueado_desde)
        self.assertIsNone(acceso.token_sesion)
        self.assertEqual(self.usuario.acceso, acceso)

    def test_uno_por_usuario(self):
        AccesoUsuario.objects.create(user=self.usuario)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            AccesoUsuario.objects.create(user=self.usuario)

    def test_se_borra_con_el_usuario(self):
        AccesoUsuario.objects.create(user=self.usuario)
        self.usuario.delete()
        self.assertFalse(AccesoUsuario.objects.exists())

    def test_guarda_historial(self):
        acceso = AccesoUsuario.objects.create(user=self.usuario)
        acceso.bloqueado = True
        acceso.save()
        self.assertEqual(acceso.history.count(), 2)
        self.assertEqual(acceso.history.model._meta.db_table, "accesos_usuario_historial")


class AccesoUsuarioEnPanelTests(TestCase):
    def test_las_tablas_existen_en_public(self):
        self.assertEqual(connection.schema_name, "public")
        self.assertTrue({"accesos_usuario", "accesos_usuario_historial"} <= tablas_del_esquema())

    def test_un_usuario_del_panel_tiene_su_acceso(self):
        usuario = User.objects.create_user(username="admin_prueba")
        acceso = AccesoUsuario.objects.create(user=usuario)
        self.assertEqual(usuario.acceso, acceso)
