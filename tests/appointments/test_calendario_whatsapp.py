from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class CalendarioWhatsappTests(NegocioTestCase):
    esquema = "calendario_whatsapp"
    dominio = "calendario-whatsapp.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila")
        self.con_telefono = Cliente.objects.create(nombre="Paula", apellido="Herrera", telefono="+56911112222")
        self.sin_telefono = Cliente.objects.create(nombre="Marta", apellido="Soto", telefono="")

    def miembro(self, rol, usuario):
        user = User.objects.create_user(username=usuario, email=f"{usuario}@correo.cl", password="x")
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def cita(self, cliente, dia, estado=Cita.EstadoChoices.PENDIENTE):
        return Cita.objects.create(
            cliente=cliente,
            fecha_agenda=date(2026, 10, dia),
            hora_agenda=time(10, 0),
            estado=estado,
            asignado_a=self.colaboradora,
        )

    def acciones(self, dia, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        respuesta = navegador.get(
            reverse("calendar_data"),
            {"vista": "mes", "desde": "2026-09-28", "hasta": "2026-11-01"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        return respuesta.json()["dias"][f"2026-10-{dia:02d}"]["citas"][0]["acciones"]

    def test_con_telefono_aparece_enviar_whatsapp_despues_de_ver_detalle(self):
        for dia, estado in [
            (20, Cita.EstadoChoices.PENDIENTE),
            (21, Cita.EstadoChoices.COMPLETADA),
            (22, Cita.EstadoChoices.CANCELADA),
        ]:
            self.cita(self.con_telefono, dia, estado)
            acciones = self.acciones(dia)
            self.assertEqual([accion["label"] for accion in acciones][:2], ["Ver detalle", "Enviar WhatsApp"])
            whatsapp = acciones[1]
            self.assertEqual(whatsapp["link"], reverse("client_whatsapp_modal", args=[self.con_telefono.pk]))
            self.assertEqual(whatsapp["className"], "bs-modal")
            self.assertTrue(whatsapp["iconImage"].endswith("images/common/whatsapp.svg"))

    def test_sin_telefono_no_aparece_la_opcion(self):
        self.cita(self.sin_telefono, 23)
        labels = [accion["label"] for accion in self.acciones(23)]
        self.assertNotIn("Enviar WhatsApp", labels)
        self.assertEqual(labels[0], "Ver detalle")

    def test_la_colaboradora_tambien_puede_abrir_el_modal(self):
        self.cita(self.con_telefono, 24)
        link = self.acciones(24, self.colaboradora)[1]["link"]
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.colaboradora)
        respuesta = navegador.get(link, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Enviar WhatsApp")
        self.assertContains(respuesta, "+56911112222")
