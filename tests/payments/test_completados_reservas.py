from datetime import datetime, time
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Tipo = TipoDetallePago
Estado = EstadoDetallePago


class CompletadosConReservaTests(NegocioTestCase):
    esquema = "completados_reserva"
    dominio = "completados-reserva.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        hoy = timezone.localdate()
        self.momento = timezone.make_aware(datetime.combine(hoy.replace(day=1), time(10, 0)))
        self.mes = f"{MONTH_NUMBER_TO_NAME[hoy.month]} {hoy.year}"

    def con_filas(self, nombre, total, *filas):
        pago = Pago.objects.create(
            cita=Cita.objects.create(
                cliente=self.cliente,
                fecha_agenda=self.momento.date(),
                hora_agenda=self.momento.time(),
                estado=Cita.EstadoChoices.COMPLETADA,
            ),
            monto_total_cita=Decimal(total),
            estado_pago=EstadoPago.COMPLETADO,
            fecha_pago_completado=self.momento,
            cliente_nombre=nombre,
            fecha_cita=self.momento,
        )
        for monto, tipo, estado in filas:
            DetallePago.objects.create(
                pago=pago,
                fecha_pago=self.momento,
                monto_pago=Decimal(monto),
                metodo_pago=MetodoPago.EFECTIVO,
                tipo_detalle=tipo,
                estado_detalle=estado,
            )

    def cifras(self):
        datos = self.navegador.get(
            reverse("payments_list"),
            {"draw": 1, "start": 0, "length": 10, "months": self.mes},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        ).json()
        grafico = self.navegador.get(
            reverse("payments_weekly_income_ajax"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        ).json()
        hoja = load_workbook(
            BytesIO(self.navegador.get(reverse("payments_export"), {"months": self.mes}).content)
        ).active
        filas = list(hoja.iter_rows(values_only=True))
        columna = filas[0].index("Total de la cita")
        return {
            "lista": {fila["cliente_nombre"]: fila["total_cita_formatted"] for fila in datos["data"]},
            "tarjetas": (datos["total_cita"], datos["monto_recibido_mes"]),
            "grafico": sum(grafico["datasets"][0]["data"]),
            "excel": {fila[1]: fila[columna] for fila in filas[1:] if fila[1]},
        }

    def test_el_total_es_el_de_los_servicios_con_los_dos_modos(self):
        self.con_filas(
            "No descuenta", "20000",
            ("5000", Tipo.RESERVA, Estado.VIGENTE),
            ("20000", Tipo.ABONO, Estado.VIGENTE),
        )
        self.con_filas(
            "Descuenta", "20000",
            ("5000", Tipo.RESERVA_DESCONTABLE, Estado.VIGENTE),
            ("15000", Tipo.ABONO, Estado.VIGENTE),
        )
        por_cita = {"No descuenta": "$20.000", "Descuenta": "$20.000"}
        self.assertEqual(
            self.cifras(),
            {"lista": por_cita, "tarjetas": ("$40.000", "$40.000"), "grafico": 40000, "excel": por_cita},
        )

    def test_una_reserva_retenida_definitiva_no_suma_al_total(self):
        self.con_filas(
            "No descuenta", "20000",
            ("5000", Tipo.RESERVA, Estado.RETENIDO_DEFINITIVO),
            ("20000", Tipo.ABONO, Estado.VIGENTE),
        )
        self.con_filas(
            "Descuenta", "25000",
            ("5000", Tipo.RESERVA_DESCONTABLE, Estado.RETENIDO_DEFINITIVO),
            ("20000", Tipo.ABONO, Estado.VIGENTE),
        )
        por_cita = {"No descuenta": "$20.000", "Descuenta": "$20.000"}
        self.assertEqual(
            self.cifras(),
            {"lista": por_cita, "tarjetas": ("$40.000", "$40.000"), "grafico": 40000, "excel": por_cita},
        )
