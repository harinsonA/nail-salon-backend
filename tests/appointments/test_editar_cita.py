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


class EditarCitaTests(NegocioTestCase):
    esquema = "editar_cita"
    dominio = "editar-cita.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana", "Ana", "Pérez")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila", "Camila", "Rojas")
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        self.otra_cliente = Cliente.objects.create(nombre="Marta", apellido="Soto")
        categoria = Categoria.objects.create(nombre="Manos")
        self.manicure = Servicio.objects.create(nombre="Manicure", precio=Decimal("12000"), categoria=categoria)
        self.diseno = Servicio.objects.create(nombre="Diseño", precio=Decimal("3000"), categoria=categoria)
        self.pedicure = Servicio.objects.create(nombre="Pedicure", precio=Decimal("15000"), categoria=categoria)
        self.cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 11, 2),
            hora_agenda=time(10, 30),
            observaciones="Prefiere tonos nude.",
            creado_por=self.encargada,
            asignado_a=self.colaboradora,
        )
        self.linea_manicure = self.detalle(self.manicure, precio=Decimal("10000"), cantidad=1, descuento=Decimal("1000"))
        self.linea_diseno = self.detalle(self.diseno, precio=Decimal("3000"), cantidad=2, descuento=Decimal("0"))

    def miembro(self, rol, usuario, nombre, apellido):
        user = User.objects.create_user(
            username=usuario, email=f"{usuario}@correo.cl", password="x", first_name=nombre, last_name=apellido
        )
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def detalle(self, servicio, precio, cantidad, descuento):
        return DetalleCita.objects.create(
            cita=self.cita,
            servicio=servicio,
            nombre_servicio=servicio.nombre,
            precio_servicio=precio,
            cantidad_servicios=cantidad,
            descuento=descuento,
            precio_acordado=precio * cantidad - descuento,
        )

    def navegador(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def abrir(self, usuario=None, cita=None):
        url = reverse("agenda_update_modal", args=[(cita or self.cita).pk])
        return self.navegador(usuario or self.encargada).get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def guardar(self, servicios, usuario=None, cita=None, **datos):
        payload = {
            "client": self.cliente.pk,
            "assigned_to": self.colaboradora.pk,
            "date": "2026-11-02",
            "time": "10:30",
            "observations": "Prefiere tonos nude.",
            "services": json.dumps(servicios),
            **datos,
        }
        url = reverse("agenda_update_modal", args=[(cita or self.cita).pk])
        return self.navegador(usuario or self.encargada).post(url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def errores(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        return {error["id_element"]: error["error"] for error in respuesta.json()["errors"]}

    def test_abre_el_modal_de_crear_con_la_cita_cargada(self):
        respuesta = self.abrir()
        self.assertTemplateUsed(respuesta, "appointments/agenda_create_modal.html")
        self.assertContains(respuesta, "Editar cita: Paula Herrera")
        self.assertContains(respuesta, "Guardar cambios")
        self.assertContains(respuesta, 'value="2026-11-02"')
        self.assertContains(respuesta, 'value="10:30"')
        self.assertContains(respuesta, "Prefiere tonos nude.")
        configuracion = respuesta.context["appointment_form_config"]
        self.assertEqual(configuracion["appointmentId"], self.cita.pk)
        lineas = {linea["service"]["nombre"]: linea for linea in configuracion["lines"]}
        self.assertEqual(lineas["Manicure"]["detalle"], self.linea_manicure.pk)
        self.assertEqual(lineas["Manicure"]["service"]["precio"], 10000)
        self.assertEqual((lineas["Diseño"]["quantity"], lineas["Diseño"]["discount"]), (2, 0))

    def test_guarda_los_cambios_y_respeta_el_precio_original(self):
        respuesta = self.guardar(
            [
                {"detalle": self.linea_manicure.pk, "cantidad": 2, "descuento": 500},
                {"id": self.pedicure.pk, "cantidad": 1, "descuento": 0},
            ],
            client=self.otra_cliente.pk,
            assigned_to=self.encargada.pk,
            date="2026-11-03",
            time="16:00",
            observations="Cambió de hora.",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["fecha"], "2026-11-03")
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.cliente, self.otra_cliente)
        self.assertEqual(self.cita.asignado_a, self.encargada)
        self.assertEqual((self.cita.fecha_agenda, self.cita.hora_agenda), (date(2026, 11, 3), time(16, 0)))
        self.assertEqual(self.cita.observaciones, "Cambió de hora.")
        self.assertEqual(self.cita.creado_por, self.encargada)
        detalles = {detalle.nombre_servicio: detalle for detalle in self.cita.detalles.all()}
        self.assertEqual(set(detalles), {"Manicure", "Pedicure"})
        self.assertEqual(detalles["Manicure"].pk, self.linea_manicure.pk)
        self.assertEqual(detalles["Manicure"].precio_servicio, Decimal("10000"))
        self.assertEqual(detalles["Manicure"].precio_acordado, Decimal("19500"))
        self.assertEqual(detalles["Pedicure"].precio_acordado, Decimal("15000"))

    def test_una_linea_existente_sigue_valida_si_el_servicio_se_desactivo(self):
        self.diseno.estado = Servicio.EstadoChoices.INACTIVO
        self.diseno.save()
        respuesta = self.guardar([{"detalle": self.linea_diseno.pk, "cantidad": 1, "descuento": 0}])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(list(self.cita.detalles.values_list("nombre_servicio", flat=True)), ["Diseño"])

    def test_no_permite_repetir_un_servicio_que_ya_estaba(self):
        errores = self.errores(
            self.guardar(
                [
                    {"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 0},
                    {"id": self.manicure.pk, "cantidad": 1, "descuento": 0},
                ]
            )
        )
        self.assertEqual(errores["id_services"], "Un servicio no puede repetirse en la misma cita.")

    def test_no_acepta_detalles_de_otra_cita(self):
        otra = Cita.objects.create(cliente=self.cliente, fecha_agenda=date(2026, 11, 4), hora_agenda=time(9, 0))
        ajeno = DetalleCita.objects.create(
            cita=otra, servicio=self.manicure, nombre_servicio="Manicure", precio_servicio=1, precio_acordado=1
        )
        errores = self.errores(self.guardar([{"detalle": ajeno.pk, "cantidad": 1, "descuento": 0}]))
        self.assertEqual(errores["id_services"], "Los servicios enviados no son válidos.")
        self.assertEqual(self.cita.detalles.count(), 2)

    def test_el_descuento_se_valida_contra_el_precio_original(self):
        errores = self.errores(self.guardar([{"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 11000}]))
        self.assertIn("Manicure", errores["id_services"])

    def test_solo_se_editan_citas_pendientes(self):
        self.cita.estado = Cita.EstadoChoices.COMPLETADA
        self.cita.save()
        self.assertEqual(self.abrir().status_code, 404)

    def test_la_colaboradora_edita_solo_las_suyas_y_sigue_asignada(self):
        ajena = Cita.objects.create(
            cliente=self.cliente, fecha_agenda=date(2026, 11, 2), hora_agenda=time(9, 0), asignado_a=self.encargada
        )
        self.assertEqual(self.abrir(self.colaboradora, ajena).status_code, 404)
        respuesta = self.guardar(
            [{"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 0}],
            usuario=self.colaboradora,
            assigned_to=self.encargada.pk,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.asignado_a, self.colaboradora)

    def test_las_horas_ocupadas_no_cuentan_la_cita_que_se_edita(self):
        Cita.objects.create(cliente=self.otra_cliente, fecha_agenda=date(2026, 11, 2), hora_agenda=time(12, 0))
        respuesta = self.navegador(self.encargada).get(
            reverse("available_hours_ajax"),
            {"fecha": "2026-11-02", "excluir": self.cita.pk},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual([hora["hora"] for hora in respuesta.json()["horas"]], ["12:00"])

    def test_un_descuento_del_100_por_ciento_queda_en_cero_al_editar(self):
        respuesta = self.guardar(
            [
                {"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 10000},
                {"detalle": self.linea_diseno.pk, "cantidad": 2, "descuento": 0},
            ]
        )
        self.assertEqual(respuesta.status_code, 200)
        self.linea_manicure.refresh_from_db()
        self.assertEqual(self.linea_manicure.precio_acordado, Decimal("0"))
        panel = self.navegador(self.encargada).get(
            reverse("agenda_see_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(panel.context["total"], "$6.000")

    def test_un_servicio_gratis_no_toma_el_precio_del_catalogo_al_editar(self):
        gratis = self.detalle(self.pedicure, precio=Decimal("0"), cantidad=1, descuento=Decimal("0"))
        respuesta = self.guardar(
            [
                {"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 1000},
                {"detalle": self.linea_diseno.pk, "cantidad": 2, "descuento": 0},
                {"detalle": gratis.pk, "cantidad": 1, "descuento": 0},
            ]
        )
        self.assertEqual(respuesta.status_code, 200)
        gratis.refresh_from_db()
        self.assertEqual((gratis.precio_servicio, gratis.precio_acordado), (Decimal("0"), Decimal("0")))

    def test_un_servicio_nuevo_con_100_por_ciento_de_descuento_queda_en_cero(self):
        respuesta = self.guardar(
            [
                {"detalle": self.linea_manicure.pk, "cantidad": 1, "descuento": 1000},
                {"detalle": self.linea_diseno.pk, "cantidad": 2, "descuento": 0},
                {"id": self.pedicure.pk, "cantidad": 2, "descuento": 30000},
            ]
        )
        self.assertEqual(respuesta.status_code, 200)
        nueva = DetalleCita.objects.get(cita=self.cita, servicio=self.pedicure)
        self.assertEqual(nueva.precio_acordado, Decimal("0"))

    def test_sin_precio_acordado_se_calcula_con_cantidad_y_descuento(self):
        linea = DetalleCita.objects.create(
            cita=self.cita, servicio=self.pedicure, cantidad_servicios=2, descuento=Decimal("1000")
        )
        self.assertEqual((linea.precio_servicio, linea.precio_acordado), (Decimal("15000"), Decimal("29000")))
