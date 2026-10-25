from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django_tenants.utils import get_public_schema_name, schema_context

from apps.profiles.models import Perfil
from apps.tenancy.models import Dominio, Negocio, Persona
from apps.tenancy.propietario import sync_owner_data
from apps.tenancy.tasks import crear_propietario
from tests.base import NegocioTestCase

User = get_user_model()


class SincronizarPropietarioTests(NegocioTestCase):
    esquema = "sincronizar"

    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(
            schema_name=get_public_schema_name(), nombre="Hi Agenda"
        )
        Dominio.objects.create(
            domain="admin.localhost", tenant=publico, is_primary=True
        )
        cls.admin = User.objects.create_superuser(username="admin", password="x")

    def setUp(self):
        super().setUp()
        with schema_context(self.esquema):
            self.propietario = User.objects.create_user(
                username="maria", email="maria@correo.cl", first_name="Titular"
            )
            Perfil.objects.filter(user=self.propietario).update(
                rol=Perfil.Rol.PROPIETARIO
            )
            self.colaboradora = User.objects.create_user(
                username="laura", email="laura@correo.cl", first_name="Laura"
            )
        connection.set_schema_to_public()
        self.titular = Persona.objects.get(pk=self.negocio.titular_id)

    def datos_en_el_negocio(self, usuario=None):
        with schema_context(self.esquema):
            usuario = User.objects.select_related("perfil").get(
                pk=(usuario or self.propietario).pk
            )
            return (
                usuario.first_name,
                usuario.last_name,
                usuario.perfil.pais,
                usuario.perfil.tipo_identificador_nacional,
                usuario.perfil.identificador_nacional,
            )

    def historial_del_perfil(self):
        with schema_context(self.esquema):
            return Perfil.objects.get(user=self.propietario).history.count()

    def test_copia_nombre_e_identificador_al_propietario_de_cada_negocio(self):
        Persona.objects.filter(pk=self.titular.pk).update(
            nombres="María José",
            apellidos="Rojas",
            pais="VE",
            tipo_identificador_nacional="cedula",
            identificador_nacional="V-12345678",
        )
        sync_owner_data(Persona.objects.get(pk=self.titular.pk))
        self.assertEqual(
            self.datos_en_el_negocio(),
            ("María José", "Rojas", "VE", "cedula", "V-12345678"),
        )
        self.assertEqual(
            self.datos_en_el_negocio(self.colaboradora), ("Laura", "", None, None, None)
        )
        with schema_context(self.esquema):
            ultimo = Perfil.objects.get(user=self.propietario).history.first()
            self.assertEqual(
                ultimo.history_change_reason,
                "Datos del propietario actualizados desde el panel",
            )
            self.assertIsNone(ultimo.history_user_id)

    def test_sin_cambios_no_toca_el_negocio(self):
        sync_owner_data(self.titular)
        antes = self.historial_del_perfil()
        sync_owner_data(self.titular)
        self.assertEqual(self.historial_del_perfil(), antes)

    def test_un_negocio_sin_esquema_se_salta(self):
        Negocio.objects.create(
            schema_name="sin_esquema", nombre="Sin esquema", titular=self.titular
        )
        sync_owner_data(self.titular)
        self.assertEqual(self.datos_en_el_negocio()[0], self.titular.nombres)

    def test_editar_al_propietario_en_el_panel_actualiza_su_negocio(self):
        panel = Client(HTTP_HOST="admin.localhost")
        panel.force_login(self.admin)
        respuesta = panel.post(
            f"/admin/tenancy/persona/{self.titular.pk}/change/modal/",
            {
                "national_id_country": "MX",
                "national_id_type": "curp",
                "national_id": "BOXW310820HNERXN09",
                "first_name": "Carla",
                "second_name": "",
                "first_surname": "Soto",
                "second_surname": "",
                "notes": "",
                "correos-TOTAL_FORMS": "1",
                "correos-INITIAL_FORMS": "0",
                "correos-0-correo": "carla@correo.cl",
                "correos-0-es_principal": "on",
                "telefonos-TOTAL_FORMS": "0",
                "telefonos-INITIAL_FORMS": "0",
                "direcciones-TOTAL_FORMS": "0",
                "direcciones-INITIAL_FORMS": "0",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            self.datos_en_el_negocio(),
            ("Carla", "Soto", "MX", "curp", "BOXW310820HNERXN09"),
        )

    def test_el_propietario_de_un_negocio_nuevo_nace_con_los_datos_del_titular(self):
        Persona.objects.filter(pk=self.titular.pk).update(
            apellidos="Rojas",
            pais="CL",
            tipo_identificador_nacional="rut",
            identificador_nacional="12345678-5",
        )
        negocio = Negocio.objects.get(pk=self.negocio.pk)
        with schema_context(self.esquema):
            User.objects.filter(pk=self.propietario.pk).delete()
            crear_propietario(negocio, "nueva@correo.cl", None)
            nuevo = User.objects.select_related("perfil").get(email="nueva@correo.cl")
            self.assertEqual(nuevo.perfil.rol, Perfil.Rol.PROPIETARIO)
            self.assertEqual(
                (
                    nuevo.first_name,
                    nuevo.last_name,
                    nuevo.perfil.pais,
                    nuevo.perfil.identificador_nacional,
                ),
                (negocio.titular.nombres, "Rojas", "CL", "12345678-5"),
            )
