from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.tenancy.estados import cambiar_estado, estados_posibles
from apps.tenancy.models import Dominio, Negocio, Persona
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()
Estado = Negocio.Estado


def url_panel(nombre, *args):
    return reverse(f"admin:{nombre}", args=args, urlconf=settings.PUBLIC_SCHEMA_URLCONF)


class CambiarEstadoTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        self.negocio = Negocio.objects.create(
            schema_name="el_corte", nombre="El Corte", titular=Persona.objects.create(nombres="X"), estado=Estado.ACTIVO
        )

    def test_el_cambio_queda_en_el_historial_con_motivo_y_autor(self):
        admin = User.objects.create_superuser(username="admin", password="x")
        cambiar_estado(self.negocio, Estado.MOROSO, "  dos meses sin pago ", admin)
        ultimo = self.negocio.history.first()
        self.assertEqual(ultimo.estado, Estado.MOROSO)
        self.assertEqual(ultimo.history_change_reason, "dos meses sin pago")
        self.assertEqual(ultimo.history_user, admin)

    def test_el_motivo_es_obligatorio(self):
        with self.assertRaises(ValidationError):
            cambiar_estado(self.negocio, Estado.PAUSADO, "   ")
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.estado, Estado.ACTIVO)

    def test_solo_se_permiten_los_cambios_del_diagrama(self):
        self.assertEqual(estados_posibles(self.negocio), [Estado.MOROSO, Estado.PAUSADO, Estado.CANCELADO])
        cambiar_estado(self.negocio, Estado.CANCELADO, "dejó de ser cliente")
        self.assertEqual(estados_posibles(self.negocio), [Estado.ACTIVO])
        with self.assertRaises(ValidationError):
            cambiar_estado(self.negocio, Estado.MOROSO, "no aplica")
        preparando = Negocio(estado=Estado.PREPARANDO)
        self.assertEqual(estados_posibles(preparando), [])

    def test_el_comando_cambia_el_estado_por_subdominio(self):
        salida = StringIO()
        call_command("cambiar_estado_negocio", "el-corte", "pausado", motivo="pedido del titular", stdout=salida)
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.estado, Estado.PAUSADO)
        self.assertIn("Activo → Pausado", salida.getvalue())
        with self.assertRaises(CommandError):
            call_command("cambiar_estado_negocio", "el-corte", "moroso", motivo="no aplica", stdout=StringIO())
        with self.assertRaises(CommandError):
            call_command("cambiar_estado_negocio", "no-existe", "activo", motivo="x", stdout=StringIO())


class EstadoEnLaAgendaTests(NegocioTestCase):
    esquema = "estados"
    dominio = "estados.localhost"

    def poner_en(self, estado):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=estado)

    def navegador_de(self, rol):
        usuario = User.objects.create_user(username=rol, email=f"{rol}@correo.cl")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def test_preparando_pausado_y_cancelado_no_dejan_entrar_a_nadie(self):
        for estado, codigo, texto in (
            (Estado.PREPARANDO, 503, "Estamos preparando tu agenda"),
            (Estado.PAUSADO, 410, "Servicio suspendido"),
            (Estado.CANCELADO, 410, "Servicio finalizado"),
        ):
            with self.subTest(estado=estado):
                self.poner_en(estado)
                anonimo = Client(HTTP_HOST=self.dominio)
                self.assertContains(anonimo.get(reverse("login")), texto, status_code=codigo)
                ajax = anonimo.get(reverse("session_ping"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(ajax.status_code, codigo)

    def test_moroso_el_equipo_sigue_trabajando(self):
        self.poner_en(Estado.MOROSO)
        colaborador = self.navegador_de(Perfil.Rol.COLABORADOR)
        calendario = colaborador.get(reverse("calendar"))
        self.assertEqual(calendario.status_code, 200)
        self.assertNotContains(calendario, "pago pendiente")
        self.assertEqual(colaborador.get(reverse("incomes")).status_code, 403)

    def test_moroso_quien_administra_ve_el_aviso_y_no_entra_a_la_administracion(self):
        self.poner_en(Estado.MOROSO)
        for rol in (Perfil.Rol.PROPIETARIO, Perfil.Rol.ENCARGADO):
            with self.subTest(rol=rol):
                navegador = self.navegador_de(rol)
                calendario = navegador.get(reverse("calendar"))
                self.assertContains(calendario, "Hay un pago pendiente con Hi Agenda")
                self.assertEqual(navegador.get(reverse("clients")).status_code, 200)
                self.assertContains(navegador.get(reverse("incomes")), "Pago pendiente", status_code=402)
                ajax = navegador.get(reverse("incomes_list"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
                self.assertEqual(ajax.status_code, 402)

    def test_activo_funciona_sin_aviso(self):
        propietario = self.navegador_de(Perfil.Rol.PROPIETARIO)
        calendario = propietario.get(reverse("calendar"))
        self.assertEqual(calendario.status_code, 200)
        self.assertNotContains(calendario, "Hay un pago pendiente")
        self.assertEqual(propietario.get(reverse("incomes")).status_code, 200)


class CambiarEstadoDesdeElPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")
        cls.negocio = Negocio.objects.create(
            schema_name="el_corte", nombre="El Corte", titular=Persona.objects.create(nombres="X"), estado=Estado.ACTIVO
        )

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST="admin.localhost")
        self.panel.force_login(self.admin)

    def test_la_ficha_tiene_el_boton_y_el_cambio_queda_con_su_autor(self):
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, url_panel("tenancy_negocio_estado", self.negocio.pk))
        respuesta = self.panel.post(
            url_panel("tenancy_negocio_estado", self.negocio.pk), {"estado": "moroso", "motivo": "dos meses sin pago"}
        )
        self.assertRedirects(
            respuesta, url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.estado, Estado.MOROSO)
        self.assertEqual(self.negocio.history.first().history_user, self.admin)

    def test_sin_motivo_o_con_un_estado_no_permitido_no_cambia(self):
        url = url_panel("tenancy_negocio_estado", self.negocio.pk)
        for datos in ({"estado": "moroso", "motivo": ""}, {"estado": "preparando", "motivo": "x"}):
            with self.subTest(datos=datos):
                self.assertEqual(self.panel.post(url, datos).status_code, 200)
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.estado, Estado.ACTIVO)
