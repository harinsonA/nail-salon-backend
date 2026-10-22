import json
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol

FECHA = "2026-11-02"


class CitaBase(NegocioTestCase):
    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana", "Ana", "Pérez")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila", "Camila", "Rojas")
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        categoria = Categoria.objects.create(nombre="Manos")
        self.manicure = Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=categoria)
        self.diseno = Servicio.objects.create(nombre="Diseño", precio=Decimal("3000"), categoria=categoria)

    def miembro(self, rol, usuario, nombre, apellido):
        user = User.objects.create_user(
            username=usuario, email=f"{usuario}@correo.cl", password="x", first_name=nombre, last_name=apellido
        )
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def navegador(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def url(self, dia=FECHA):
        return reverse("create_appointment_from_calendar", args=[dia])

    def crear(self, usuario=None, servicios=None, **datos):
        servicios = servicios if servicios is not None else [{"id": self.manicure.pk, "cantidad": 1, "descuento": 0}]
        payload = {
            "client": self.cliente.pk,
            "assigned_to": self.encargada.pk,
            "date": FECHA,
            "time": "10:30",
            "services": json.dumps(servicios),
            **datos,
        }
        return self.navegador(usuario or self.encargada).post(self.url(), payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def errores(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        return {error["id_element"]: error["error"] for error in respuesta.json()["errors"]}


class CrearCitaTests(CitaBase):
    esquema = "crear_cita"
    dominio = "crear-cita.localhost"

    def test_abre_el_modal_con_la_fecha_del_calendario(self):
        respuesta = self.navegador(self.encargada).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(respuesta, "appointments/agenda_create_modal.html")
        self.assertContains(respuesta, f'value="{FECHA}"')
        configuracion = respuesta.context["appointment_form_config"]
        self.assertEqual({servicio["nombre"] for servicio in configuracion["services"]}, {"Manicure", "Diseño"})
        self.assertEqual(configuracion["currentUser"], self.encargada.pk)

    def test_una_fecha_pasada_abre_con_la_de_hoy(self):
        respuesta = self.navegador(self.encargada).get(self.url("2020-01-01"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(respuesta, f'value="{timezone.localdate().isoformat()}"')

    def test_entrar_directo_a_la_url_vuelve_al_calendario(self):
        respuesta = self.navegador(self.encargada).get(self.url())
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)

    def test_crea_la_cita_con_sus_servicios_y_quien_la_agenda(self):
        respuesta = self.crear(
            servicios=[
                {"id": self.manicure.pk, "cantidad": 1, "descuento": 2000},
                {"id": self.diseno.pk, "cantidad": 2, "descuento": 0},
            ],
            assigned_to=self.colaboradora.pk,
            observations="Prefiere tonos nude.",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["fecha"], FECHA)
        self.assertIn("lunes 2 noviembre 2026, 10:30", respuesta.json()["message"])
        cita = Cita.objects.get()
        self.assertEqual((cita.fecha_agenda, cita.hora_agenda), (date(2026, 11, 2), time(10, 30)))
        self.assertEqual(cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(cita.creado_por, self.encargada)
        self.assertEqual(cita.asignado_a, self.colaboradora)
        self.assertEqual(cita.observaciones, "Prefiere tonos nude.")
        detalles = {detalle.nombre_servicio: detalle for detalle in cita.detalles.all()}
        self.assertEqual(detalles["Manicure"].precio_acordado, Decimal("8000"))
        self.assertEqual(detalles["Manicure"].descuento, Decimal("2000"))
        self.assertEqual(detalles["Diseño"].precio_acordado, Decimal("6000"))
        self.assertEqual(detalles["Diseño"].cantidad_servicios, 2)

    def test_la_colaboradora_solo_agenda_para_si_misma(self):
        respuesta = self.crear(usuario=self.colaboradora, assigned_to=self.encargada.pk)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Cita.objects.get().asignado_a, self.colaboradora)

    def test_la_colaboradora_solo_se_ve_a_si_misma_en_asignada(self):
        respuesta = self.navegador(self.colaboradora).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        campo = respuesta.context["form"]["assigned_to"]
        self.assertEqual(list(campo.field.queryset), [self.colaboradora])
        self.assertTrue(campo.field.disabled)

    def test_valida_los_campos_obligatorios(self):
        errores = self.errores(self.crear(servicios=[], client="", date="", time=""))
        self.assertEqual(set(errores), {"id_client", "id_date", "id_time", "id_services"})
        self.assertEqual(errores["id_services"], "Agrega al menos un servicio.")
        self.assertFalse(Cita.objects.exists())

    def test_el_descuento_no_puede_superar_el_precio(self):
        errores = self.errores(self.crear(servicios=[{"id": self.manicure.pk, "cantidad": 1, "descuento": 10001}]))
        self.assertIn("Manicure", errores["id_services"])
        self.assertFalse(Cita.objects.exists())

    def test_no_acepta_servicios_inactivos_ni_repetidos(self):
        self.diseno.estado = Servicio.EstadoChoices.INACTIVO
        self.diseno.save()
        inactivo = self.errores(self.crear(servicios=[{"id": self.diseno.pk, "cantidad": 1, "descuento": 0}]))
        repetido = self.errores(
            self.crear(servicios=[{"id": self.manicure.pk, "cantidad": 1}, {"id": self.manicure.pk, "cantidad": 1}])
        )
        self.assertEqual(inactivo["id_services"], "Uno de los servicios ya no está disponible.")
        self.assertEqual(repetido["id_services"], "Un servicio no puede repetirse en la misma cita.")

    def test_la_cantidad_debe_ser_valida(self):
        errores = self.errores(self.crear(servicios=[{"id": self.manicure.pk, "cantidad": 0, "descuento": 0}]))
        self.assertIn("entre 1 y 99", errores["id_services"])

    def test_las_observaciones_no_superan_250_caracteres(self):
        errores = self.errores(self.crear(observations="a" * 251))
        self.assertIn("id_observations", errores)


class HorasOcupadasTests(CitaBase):
    esquema = "horas_ocupadas"
    dominio = "horas-ocupadas.localhost"

    def cita(self, hora, asignada, estado=Cita.EstadoChoices.PENDIENTE):
        cita = Cita.objects.create(
            cliente=self.cliente, fecha_agenda=date(2026, 11, 2), hora_agenda=time(*hora), estado=estado, asignado_a=asignada
        )
        DetalleCita.objects.create(cita=cita, servicio=self.manicure, nombre_servicio="Manicure", precio_servicio=10000, precio_acordado=10000)
        return cita

    def ocupadas(self, usuario, asignada):
        respuesta = self.navegador(usuario).get(
            reverse("available_hours_ajax"), {"fecha": FECHA, "asignada": asignada.pk}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        return respuesta.json()["horas"]

    def test_agrupa_por_hora_y_marca_las_de_la_persona_asignada(self):
        self.cita((10, 0), self.encargada)
        self.cita((10, 0), self.colaboradora)
        self.cita((12, 0), self.colaboradora)
        self.cita((15, 0), self.encargada, estado=Cita.EstadoChoices.CANCELADA)
        self.assertEqual(
            self.ocupadas(self.encargada, self.encargada),
            [
                {"hora": "10:00", "total": 2, "de_asignada": True},
                {"hora": "12:00", "total": 1, "de_asignada": False},
            ],
        )

    def test_la_colaboradora_solo_ve_sus_horas(self):
        self.cita((10, 0), self.encargada)
        self.cita((12, 0), self.colaboradora)
        self.assertEqual(self.ocupadas(self.colaboradora, self.colaboradora), [{"hora": "12:00", "total": 1, "de_asignada": True}])

    def test_sin_fecha_no_hay_horas(self):
        respuesta = self.navegador(self.encargada).get(reverse("available_hours_ajax"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.json(), {"horas": []})
