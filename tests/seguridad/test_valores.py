from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.seguridad.checks import check_lock_settings


class ValoresDeSeguridadTests(SimpleTestCase):
    def test_valores_acordados(self):
        self.assertEqual(settings.SECURITY_TEMPORARY_LOCK_FAILURES, 5)
        self.assertEqual(settings.SECURITY_TEMPORARY_LOCK_MINUTES, 15)
        self.assertEqual(settings.SECURITY_PERMANENT_LOCK_FAILURES, 10)
        self.assertTrue(settings.SECURITY_SINGLE_SESSION)

    def test_los_valores_acordados_pasan_el_chequeo(self):
        self.assertEqual(check_lock_settings(None), [])

    @override_settings(SECURITY_TEMPORARY_LOCK_FAILURES=10, SECURITY_PERMANENT_LOCK_FAILURES=10)
    def test_el_temporal_debe_ser_menor_que_el_definitivo(self):
        self.assertEqual([error.id for error in check_lock_settings(None)], ["seguridad.E001"])

    @override_settings(SECURITY_TEMPORARY_LOCK_FAILURES=0)
    def test_el_temporal_debe_ser_al_menos_uno(self):
        self.assertEqual([error.id for error in check_lock_settings(None)], ["seguridad.E001"])

    @override_settings(SECURITY_TEMPORARY_LOCK_MINUTES=0)
    def test_el_bloqueo_temporal_dura_al_menos_un_minuto(self):
        self.assertEqual([error.id for error in check_lock_settings(None)], ["seguridad.E002"])
