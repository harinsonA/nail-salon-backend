from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.seguridad.access import (
    LockState,
    lock_status,
    register_failure,
    register_login,
    unlock,
)
from apps.seguridad.models import AccesoUsuario
from tests.base import NegocioTestCase

User = get_user_model()


class ReglasDelBloqueoTests(NegocioTestCase):
    esquema = "reglas"

    def setUp(self):
        super().setUp()
        self.usuario = User.objects.create_user(username="ana", email="ana@correo.cl")
        self.ahora = timezone.now()

    def fallar(self, veces, minutos=0):
        estado = None
        for _ in range(veces):
            estado = register_failure(
                self.usuario, now=self.ahora + timedelta(minutes=minutos)
            )
        return estado

    def acceso(self):
        return AccesoUsuario.objects.get(user=self.usuario)

    def test_sin_fila_esta_libre(self):
        estado = lock_status(self.usuario)
        self.assertEqual(estado.state, LockState.FREE)
        self.assertFalse(estado.is_locked)

    def test_cuatro_fallos_no_bloquean(self):
        estado = self.fallar(4)
        self.assertEqual(estado.state, LockState.FREE)
        self.assertEqual(estado.failures, 4)
        self.assertEqual(self.acceso().ultimo_intento_fallido, self.ahora)

    def test_los_fallos_sueltos_no_dejan_historial(self):
        self.fallar(4)
        self.assertEqual(self.acceso().history.count(), 1)

    def test_el_quinto_fallo_bloquea_quince_minutos(self):
        estado = self.fallar(5)
        self.assertEqual(estado.state, LockState.TEMPORARY)
        self.assertEqual(estado.until, self.ahora + timedelta(minutes=15))
        self.assertEqual(
            self.acceso().history.first().history_change_reason,
            "Bloqueo temporal por intentos fallidos",
        )

    def test_durante_el_bloqueo_los_fallos_no_cuentan(self):
        self.fallar(5)
        estado = self.fallar(3, minutos=10)
        self.assertEqual(estado.state, LockState.TEMPORARY)
        self.assertEqual(self.acceso().intentos_fallidos, 5)

    def test_al_vencer_el_bloqueo_se_puede_volver_a_intentar(self):
        self.fallar(5)
        self.assertFalse(
            lock_status(
                self.usuario, now=self.ahora + timedelta(minutes=15, seconds=1)
            ).is_locked
        )
        estado = self.fallar(1, minutos=16)
        self.assertEqual(estado.state, LockState.FREE)
        self.assertEqual(estado.failures, 6)

    def test_el_decimo_fallo_bloquea_definitivo(self):
        self.fallar(5)
        estado = self.fallar(5, minutos=16)
        self.assertEqual(estado.state, LockState.PERMANENT)
        acceso = self.acceso()
        self.assertTrue(acceso.bloqueado)
        self.assertEqual(acceso.bloqueado_desde, self.ahora + timedelta(minutes=16))
        self.assertIsNone(acceso.bloqueado_hasta)
        self.assertEqual(
            acceso.history.first().history_change_reason,
            "Bloqueo definitivo por intentos fallidos",
        )

    def test_el_bloqueo_definitivo_no_vence(self):
        self.fallar(5)
        self.fallar(5, minutos=16)
        self.assertEqual(
            lock_status(self.usuario, now=self.ahora + timedelta(days=30)).state,
            LockState.PERMANENT,
        )
        self.fallar(3, minutos=60)
        self.assertEqual(self.acceso().intentos_fallidos, 10)

    def test_entrar_bien_reinicia_el_conteo(self):
        self.fallar(3)
        register_login(self.usuario)
        self.assertEqual(self.acceso().intentos_fallidos, 0)
        self.assertEqual(self.fallar(4).state, LockState.FREE)

    def test_entrar_bien_no_quita_el_bloqueo_definitivo(self):
        self.fallar(5)
        self.fallar(5, minutos=16)
        register_login(self.usuario)
        self.assertTrue(self.acceso().bloqueado)
        self.assertEqual(self.acceso().intentos_fallidos, 10)

    def test_desbloquear_reinicia_todo_y_deja_historial(self):
        self.fallar(5)
        self.fallar(5, minutos=16)
        self.assertTrue(unlock(self.usuario, "Desbloqueado por la encargada"))
        acceso = self.acceso()
        self.assertFalse(acceso.bloqueado)
        self.assertIsNone(acceso.bloqueado_desde)
        self.assertIsNone(acceso.bloqueado_hasta)
        self.assertEqual(acceso.intentos_fallidos, 0)
        self.assertEqual(
            acceso.history.first().history_change_reason,
            "Desbloqueado por la encargada",
        )
        self.assertEqual(self.fallar(4).state, LockState.FREE)

    def test_desbloquear_quita_el_bloqueo_temporal(self):
        self.fallar(5)
        self.assertTrue(unlock(self.usuario, "Desbloqueado"))
        self.assertFalse(lock_status(self.usuario).is_locked)

    def test_desbloquear_a_quien_no_esta_bloqueado_no_cambia_nada(self):
        self.assertFalse(unlock(self.usuario, "Desbloqueado"))
        self.fallar(2)
        self.assertFalse(unlock(self.usuario, "Desbloqueado"))
        self.assertEqual(self.acceso().intentos_fallidos, 2)

    @override_settings(
        SECURITY_TEMPORARY_LOCK_FAILURES=2,
        SECURITY_TEMPORARY_LOCK_MINUTES=1,
        SECURITY_PERMANENT_LOCK_FAILURES=3,
    )
    def test_respeta_los_valores_configurados(self):
        estado = self.fallar(2)
        self.assertEqual(estado.state, LockState.TEMPORARY)
        self.assertEqual(estado.until, self.ahora + timedelta(minutes=1))
        self.assertEqual(self.fallar(1, minutos=2).state, LockState.PERMANENT)


class ReglasDelBloqueoEnPanelTests(TestCase):
    def test_un_usuario_del_panel_se_bloquea_igual(self):
        usuario = User.objects.create_user(username="admin_prueba")
        ahora = timezone.now()
        for _ in range(5):
            estado = register_failure(usuario, now=ahora)
        self.assertEqual(estado.state, LockState.TEMPORARY)
        self.assertTrue(unlock(usuario, "Desbloqueado"))
