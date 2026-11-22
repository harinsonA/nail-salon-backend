from django.test import Client as Browser
from django.urls import reverse

from apps.payments.choices import MetodoPago
from apps.profiles.models import Perfil
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class ReservationSettingsApiTests(ApiTestCase):
    esquema = "api_reservation_settings"
    dominio = "api-reservation-settings.localhost"

    def save(self, **data):
        return self.api_client.patch(reverse("api_reservation_settings"), data, format="json")

    def saved(self):
        return (
            RESERVATION_ENABLED.get(),
            RESERVATION_DISCOUNTS_TOTAL.get(),
            RESERVATION_AMOUNT.get(),
            RESERVATION_PAYMENT_METHOD.get(),
        )

    def turn_on(self):
        RESERVATION_ENABLED.set(True)
        RESERVATION_DISCOUNTS_TOTAL.set(True)
        RESERVATION_AMOUNT.set(5000)
        RESERVATION_PAYMENT_METHOD.set(MetodoPago.TRANSFERENCIA)

    def test_administration_saves_and_gets_the_me_preferences(self):
        for rol, amount in ((Rol.PROPIETARIO, 5000), (Rol.ENCARGADO, 7000)):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                response = self.save(
                    enabled=True, amount=amount, discounts_total=True, payment_method=MetodoPago.TARJETA
                )
                self.assertEqual(response.status_code, 200, response.content)
                data = response.json()
                self.assertEqual(data["message"], "La configuración de las citas se guardó.")
                self.assertEqual(data["preferences"]["reservation_enabled"], True)
                self.assertEqual(data["preferences"]["reservation_amount"], amount)
                self.assertEqual(data["preferences"]["reservation_discounts_total"], True)
                self.assertEqual(data["preferences"]["reservation_payment_method"], MetodoPago.TARJETA)
                me = self.api_client.get(reverse("api_me")).json()["preferences"]
                self.assertEqual(me, data["preferences"])
        self.assertEqual(self.saved(), (True, True, 7000, MetodoPago.TARJETA))

    def test_only_what_changed_keeps_the_rest(self):
        self.turn_on()
        self.log_in_as(Rol.PROPIETARIO)
        response = self.save(amount=8000)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.saved(), (True, True, 8000, MetodoPago.TRANSFERENCIA))

    def test_enabled_needs_an_amount(self):
        self.log_in_as(Rol.PROPIETARIO)
        for amount in (None, 0):
            with self.subTest(amount=amount):
                response = self.save(enabled=True, amount=amount)
                self.assertApiError(response, 400, "invalid_data")
                self.assertIn("establecer el valor de la reserva", response.json()["fields"]["amount"][0])
                self.assertEqual(RESERVATION_ENABLED.get(), False)

    def test_amount_over_the_limit_is_rejected(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.save(enabled=True, amount=100_000_000)
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("amount", response.json()["fields"])

    def test_enabled_without_method_uses_cash(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.save(enabled=True, amount=5000, payment_method="")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.saved(), (True, False, 5000, MetodoPago.EFECTIVO))

    def test_turning_it_off_clears_the_other_values(self):
        self.turn_on()
        self.log_in_as(Rol.PROPIETARIO)
        response = self.save(enabled=False)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.saved(), (False, False, 0, MetodoPago.EFECTIVO))

    def test_the_web_sees_what_the_app_saved(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        self.save(enabled=True, amount=6000, payment_method=MetodoPago.TARJETA)
        browser = Browser(HTTP_HOST=self.dominio)
        browser.force_login(user)
        response = browser.get(reverse("appointment_preferences"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(response, 'value="6.000"')
        self.assertContains(response, '<option value="TARJETA" selected>')

    def test_collaborator_cannot_change_it(self):
        self.log_in_as(Rol.COLABORADOR)
        self.assertApiError(self.save(enabled=True, amount=5000), 403, "forbidden")
        self.assertEqual(RESERVATION_ENABLED.get(), False)

    def test_overdue_business_pauses_the_route(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.MOROSO)
        self.log_in_as(Rol.PROPIETARIO)
        self.assertApiError(self.save(enabled=True, amount=5000), 402, "payment_pending")
        self.assertEqual(RESERVATION_ENABLED.get(), False)
