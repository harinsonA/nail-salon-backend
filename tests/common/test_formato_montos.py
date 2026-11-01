from decimal import Decimal

from django import forms
from django.test import SimpleTestCase

from apps.common.form_fields import MoneyField
from apps.common.utils.currency import Money
from apps.common.widgets import MoneyInput


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


class CampoDeMontoTests(SimpleTestCase):
    def setUp(self):
        self.campo = MoneyField(label="Monto abonado", required=False)

    def test_el_punto_de_miles_no_cambia_el_monto(self):
        casos = [("12000", 12000), ("12.000", 12000), ("1.234.567", 1234567), (" 7.000 ", 7000), ("", None)]
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertEqual(self.campo.clean(texto), esperado)

    def test_rechaza_decimales_comas_y_negativos(self):
        casos = [
            ("12,000", "El campo 'monto abonado' debe ser un monto en pesos, sin decimales."),
            ("12.5", "El campo 'monto abonado' debe ser un monto en pesos, sin decimales."),
            ("1.2345", "El campo 'monto abonado' debe ser un monto en pesos, sin decimales."),
            ("-500", "El campo 'monto abonado' no puede ser negativo."),
        ]
        for texto, mensaje in casos:
            with self.subTest(texto=texto):
                with self.assertRaisesMessage(forms.ValidationError, mensaje):
                    self.campo.clean(texto)

    def test_el_campo_muestra_el_monto_con_punto_de_miles(self):
        html = MoneyInput().render("monto", Decimal("15000.00"))
        self.assertIn('value="15.000"', html)
        self.assertIn('inputmode="numeric"', html)
        self.assertIn("data-money", html)
        self.assertNotIn("value=", MoneyInput().render("monto", 0))
