from decimal import Decimal

from django.test import SimpleTestCase

from apps.common.utils.currency import Money


class FormatoMontosTests(SimpleTestCase):
    def test_usa_punto_de_miles_y_signo_menos_delante(self):
        casos = [
            (12000, "$12.000"),
            (1234567, "$1.234.567"),
            (500, "$500"),
            (-4000, "-$4.000"),
            (Decimal("27000.00"), "$27.000"),
        ]
        for valor, esperado in casos:
            with self.subTest(valor=valor):
                self.assertEqual(Money.format(valor), esperado)

    def test_vacio_es_cero(self):
        self.assertEqual(Money.format(None), "$0")
        self.assertEqual(Money.format(0), "$0")

    def test_redondea_a_pesos_enteros_hacia_arriba_en_la_mitad(self):
        self.assertEqual(Money.format(Decimal("12000.50")), "$12.001")
        self.assertEqual(Money.format(Decimal("12000.49")), "$12.000")
        self.assertEqual(Money.format(Decimal("-12000.50")), "-$12.001")
