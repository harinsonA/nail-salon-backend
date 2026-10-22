import json
from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class LlenadoAutomaticoTests(NegocioTestCase):
    esquema = "llenado"
    dominio = "llenado.localhost"

    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Clienta")
        categoria = Categoria.objects.create(nombre="Manos")
        self.servicio = Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=categoria)

    def crear(self, rol, nombre, apellido=""):
        usuario = User.objects.create_user(
            username=nombre,
            email=f"{nombre}@correo.cl",
            password="x",
            first_name=nombre.title(),
            last_name=apellido,
        )
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=usuario.pk)

    def navegador_de(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def crear_cita_con_servicio(self, usuario=None):
        cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
            creado_por=usuario,
            asignado_a=usuario,
        )
        DetalleCita.objects.create(cita=cita, servicio=self.servicio, precio_acordado=Decimal("10000"))
        return cita

    def completar(self, navegador, cita, **datos):
        datos = {"payment_method": "EFECTIVO", "down_payment": "0", "remaining_payment": "0", **datos}
        respuesta = navegador.post(
            reverse("agenda_confirmation_modal", args=[cita.pk]),
            datos,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        cita.refresh_from_db()
        return cita.pago

    def test_crear_cita_la_deja_creada_y_asignada_a_quien_la_agenda(self):
        colaboradora = self.crear(Rol.COLABORADOR, "camila")
        respuesta = self.navegador_de(colaboradora).post(
            reverse("create_appointment_from_calendar", args=["2026-10-20"]),
            {
                "client": self.cliente.pk,
                "date": "2026-10-20",
                "time": "10:00",
                "services": json.dumps([{"id": self.servicio.pk, "cantidad": 1, "descuento": 0}]),
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        cita = Cita.objects.get(cliente=self.cliente)
        self.assertEqual(cita.creado_por, colaboradora)
        self.assertEqual(cita.asignado_a, colaboradora)

    def test_completar_cita_registra_a_quien_la_completa_en_el_pago_y_el_abono(self):
        encargada = self.crear(Rol.ENCARGADO, "ana", "Pérez")
        colaboradora = self.crear(Rol.COLABORADOR, "camila", "Rojas")
        cita = self.crear_cita_con_servicio(colaboradora)
        pago = self.completar(self.navegador_de(encargada), cita, full_payment="on")
        self.assertEqual(pago.atendido_por, encargada)
        self.assertEqual(pago.atendido_por_nombre, "Ana Pérez")
        self.assertEqual(pago.detalles_pago.get().registrado_por, encargada)
        self.assertEqual(cita.asignado_a, colaboradora)

    def test_sin_nombre_se_guarda_el_correo_de_quien_atendio(self):
        colaboradora = User.objects.create_user(username="sin_nombre", email="sin.nombre@correo.cl", password="x")
        Perfil.objects.filter(user=colaboradora).update(debe_cambiar_clave=False)
        cita = self.crear_cita_con_servicio(colaboradora)
        pago = self.completar(self.navegador_de(colaboradora), cita, full_payment="on")
        self.assertEqual(pago.atendido_por_nombre, "sin.nombre@correo.cl")

    def test_cada_abono_registra_a_quien_lo_recibe(self):
        colaboradora = self.crear(Rol.COLABORADOR, "camila")
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        cita = self.crear_cita_con_servicio(colaboradora)
        pago = self.completar(self.navegador_de(colaboradora), cita, down_payment="4000")
        respuesta = self.navegador_de(propietaria).post(
            reverse("add_payment_modal", args=[pago.pk]),
            {
                "payment_method": "EFECTIVO",
                "full_payment": "on",
                "payment_date": "2026-10-21",
                "payment_time": "11:00",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        primero, segundo = pago.detalles_pago.order_by("pk")
        self.assertEqual(primero.registrado_por, colaboradora)
        self.assertEqual(segundo.registrado_por, propietaria)
        pago.refresh_from_db()
        self.assertEqual(pago.atendido_por, colaboradora)
