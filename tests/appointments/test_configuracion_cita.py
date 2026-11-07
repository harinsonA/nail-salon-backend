from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.calendar.constants import APPOINTMENT_PREFERENCE_FIELDS
from apps.payments.choices import MetodoPago
from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_CANCELLED,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class ConfiguracionCitaTests(NegocioTestCase):
    esquema = "configuracion_cita"
    dominio = "configuracion-cita.localhost"

    def setUp(self):
        super().setUp()
        self.propietaria = self.crear_usuario("propietaria", Rol.PROPIETARIO)
        self.encargada = self.crear_usuario("encargada", Rol.ENCARGADO)
        self.colaboradora = self.crear_usuario("colaboradora", Rol.COLABORADOR)

    def crear_usuario(self, usuario, rol):
        user = User.objects.create_user(username=usuario, email=f"{usuario}@correo.cl", password="x")
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def navegador(self, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador

    def calendario(self, usuario=None):
        return self.navegador(usuario).get(reverse("calendar"))

    def abrir(self, usuario=None):
        return self.navegador(usuario).get(
            reverse("appointment_preferences"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def guardar(self, usuario=None, **cambios):
        datos = {
            "reserva_habilitada": "on",
            "valor_reserva": "5.000",
            "reserva_metodo_pago": MetodoPago.TRANSFERENCIA,
            **cambios,
        }
        datos = {clave: valor for clave, valor in datos.items() if valor is not None}
        return self.navegador(usuario).post(
            reverse("appointment_preferences"), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def configuracion_guardada(self):
        return (
            RESERVATION_ENABLED.get(),
            RESERVATION_DISCOUNTS_TOTAL.get(),
            RESERVATION_AMOUNT.get(),
            RESERVATION_PAYMENT_METHOD.get(),
        )

    def test_el_dropdown_lleva_a_los_dos_modales(self):
        respuesta = self.calendario()
        self.assertContains(respuesta, 'data-bs-toggle="dropdown"')
        self.assertContains(respuesta, f'data-form-url="{reverse("calendar_preferences")}"')
        self.assertContains(respuesta, f'data-form-url="{reverse("appointment_preferences")}"')

    def test_la_colaboradora_no_ve_cita_y_el_servidor_se_lo_impide(self):
        respuesta = self.calendario(self.colaboradora)
        self.assertContains(respuesta, f'data-form-url="{reverse("calendar_preferences")}"')
        self.assertNotContains(respuesta, reverse("appointment_preferences"))
        self.assertEqual(self.abrir(self.colaboradora).status_code, 403)
        self.assertEqual(self.guardar(self.colaboradora).status_code, 403)
        self.assertFalse(Preference.objects.filter(key=RESERVATION_AMOUNT.key).exists())

    def test_propietaria_y_encargada_configuran(self):
        for usuario, monto in ((self.propietaria, "5.000"), (self.encargada, "7.000")):
            with self.subTest(usuario=usuario.username):
                self.assertContains(self.calendario(usuario), reverse("appointment_preferences"))
                self.assertEqual(self.abrir(usuario).status_code, 200)
                self.assertEqual(self.guardar(usuario, valor_reserva=monto).status_code, 200)
        self.assertEqual(RESERVATION_AMOUNT.get(), 7000)

    def test_el_modal_maneja_solo_los_campos_de_su_lista(self):
        respuesta = self.abrir()
        self.assertTemplateUsed(respuesta, "calendar/appointment_preferences_modal.html")
        self.assertEqual(
            respuesta.context["form"].preference_keys,
            [preference.key for preference in APPOINTMENT_PREFERENCE_FIELDS],
        )
        self.assertContains(respuesta, "Reserva")
        self.assertContains(respuesta, "Guardar")

    def test_el_monto_usa_data_money_y_no_un_campo_numerico(self):
        RESERVATION_ENABLED.set(True)
        RESERVATION_AMOUNT.set(12000)
        respuesta = self.abrir()
        self.assertContains(respuesta, "data-money")
        self.assertContains(respuesta, 'value="12.000"')
        self.assertNotContains(respuesta, 'type="number"')

    def test_el_metodo_configurado_viene_elegido(self):
        RESERVATION_ENABLED.set(True)
        RESERVATION_AMOUNT.set(5000)
        RESERVATION_PAYMENT_METHOD.set(MetodoPago.TARJETA)
        self.assertContains(self.abrir(), '<option value="TARJETA" selected>')

    def test_los_detalles_se_ocultan_si_la_reserva_esta_apagada(self):
        self.assertContains(self.abrir(), "data-reservation-details hidden")
        RESERVATION_ENABLED.set(True)
        RESERVATION_AMOUNT.set(5000)
        self.assertNotContains(self.abrir(), "data-reservation-details hidden")

    def test_guardar_encendida_deja_toda_la_configuracion(self):
        respuesta = self.guardar(reserva_descuenta_total="on")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            self.configuracion_guardada(), (True, True, 5000, MetodoPago.TRANSFERENCIA)
        )

    def test_encendida_sin_monto_o_en_cero_no_guarda_y_explica_el_error(self):
        for monto in ("", "0", None):
            with self.subTest(monto=monto):
                respuesta = self.guardar(valor_reserva=monto)
                self.assertEqual(respuesta.status_code, 400)
                errores = respuesta.json()["errors"]
                self.assertEqual(errores[0]["id_element"], "id_valor_reserva")
                self.assertIn("establecer el valor de la reserva", errores[0]["error"])
                self.assertFalse(Preference.objects.filter(key=RESERVATION_ENABLED.key).exists())

    def test_encendida_con_monto_invalido_no_guarda(self):
        for monto in ("abc", "-1", "100.000.000"):
            with self.subTest(monto=monto):
                self.assertEqual(self.guardar(valor_reserva=monto).status_code, 400)
                self.assertFalse(Preference.objects.filter(key=RESERVATION_AMOUNT.key).exists())

    def test_un_metodo_invalido_no_guarda(self):
        self.assertEqual(self.guardar(reserva_metodo_pago="BITCOIN").status_code, 400)
        self.assertFalse(Preference.objects.filter(key=RESERVATION_AMOUNT.key).exists())

    def test_al_apagarla_vuelven_el_descuento_el_monto_y_el_metodo(self):
        self.guardar(reserva_descuenta_total="on")
        respuesta = self.guardar(reserva_habilitada=None, reserva_descuenta_total="on")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.configuracion_guardada(), (False, False, 0, MetodoPago.EFECTIVO))

    def test_al_apagarla_no_importa_lo_que_traigan_los_campos_ocultos(self):
        for monto, metodo in ((None, None), ("", ""), ("abc", "BITCOIN"), ("100.000.000", "CHEQUE")):
            with self.subTest(monto=monto, metodo=metodo):
                respuesta = self.guardar(
                    reserva_habilitada=None, valor_reserva=monto, reserva_metodo_pago=metodo
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(self.configuracion_guardada(), (False, False, 0, MetodoPago.EFECTIVO))

    def test_es_del_negocio_y_otra_persona_la_ve(self):
        self.guardar(self.propietaria, reserva_descuenta_total="on")
        formulario = self.abrir(self.encargada).context["form"]
        self.assertIs(formulario.enabled_field.value(), True)
        self.assertEqual(formulario.amount_field.value(), 5000)
        guardada = Preference.objects.get(key=RESERVATION_PAYMENT_METHOD.key)
        self.assertEqual(guardada.scope_id, "")

    def test_guardar_cita_no_altera_el_calendario(self):
        CALENDAR_DEFAULT_VIEW.set("semana", user=self.encargada)
        CALENDAR_SHOW_CANCELLED.set(False, user=self.encargada)
        respuesta = self.guardar(
            calendario_vista_inicial="mes", calendario_ver_canceladas="on"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(CALENDAR_DEFAULT_VIEW.get(self.encargada), "semana")
        self.assertIs(CALENDAR_SHOW_CANCELLED.get(self.encargada), False)

    def test_guardar_el_calendario_no_altera_la_cita(self):
        self.guardar(reserva_descuenta_total="on")
        respuesta = self.navegador().post(
            reverse("calendar_preferences"),
            {"calendario_vista_inicial": "mes", "reserva_metodo_pago": MetodoPago.CHEQUE, "valor_reserva": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            self.configuracion_guardada(), (True, True, 5000, MetodoPago.TRANSFERENCIA)
        )
