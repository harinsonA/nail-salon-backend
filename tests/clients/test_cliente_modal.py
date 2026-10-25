from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()


class ClienteModalTests(NegocioTestCase):
    esquema = "clientes_modal"
    dominio = "clientes-modal.localhost"

    def setUp(self):
        super().setUp()
        usuario = User.objects.create_user(username="maria", email="maria@correo.cl")
        Perfil.objects.filter(user=usuario).update(
            rol=Perfil.Rol.PROPIETARIO, debe_cambiar_clave=False
        )
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(usuario)

    def datos(self, **cambios):
        return {
            "first_name": "Ana",
            "second_name": "",
            "first_surname": "",
            "second_surname": "",
            "national_id_country": "",
            "national_id_type": "",
            "national_id": "",
            "email": "",
            "country_phone_prefix": "+56",
            "phone": "",
            "notes": "",
            "status": "on",
            **cambios,
        }

    def crear(self, **cambios):
        return self.navegador.post(
            reverse("client_create_modal"),
            self.datos(**cambios),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def editar(self, cliente, **cambios):
        return self.navegador.post(
            reverse("client_detail_modal", kwargs={"pk": cliente.pk}),
            self.datos(**cambios),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def errores(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        return {error["id_element"]: error["error"] for error in respuesta.json()["errors"]}

    def test_el_modal_tiene_datos_basicos_y_contacto(self):
        html = self.navegador.get(
            reverse("client_create_modal"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        ).content.decode()
        basicos, contacto = html.split('id="client-pane-contact"')
        for campo in ("national_id_country", "first_name", "second_name", "first_surname", "second_surname", "notes"):
            with self.subTest(campo=campo):
                self.assertIn(f'name="{campo}"', basicos)
        self.assertLess(basicos.index('name="national_id_country"'), basicos.index('name="first_name"'))
        self.assertIn("El identificador nacional es opcional", basicos)
        self.assertIn('name="email"', contacto)
        self.assertIn('name="phone"', contacto)
        self.assertNotIn('name="email"', basicos)
        self.assertRegex(html, r'<select name="national_id_type"[^>]*disabled')

    def test_crea_un_cliente_con_los_nombres_unidos_y_sin_identificador(self):
        respuesta = self.crear(
            first_name="Ana", second_name="María", first_surname="Rojas", second_surname="Pérez"
        )
        self.assertEqual(respuesta.status_code, 200)
        cliente = Cliente.objects.get()
        self.assertEqual(
            (cliente.nombre, cliente.apellido, cliente.pais, cliente.identificador_nacional),
            ("Ana María", "Rojas Pérez", None, None),
        )

    def test_guarda_el_identificador_normalizado_y_el_pais_solo(self):
        self.crear(national_id_country="CL", national_id_type="rut", national_id="12.345.678-5")
        self.crear(first_name="Lucia", national_id_country="VE")
        self.assertEqual(
            list(
                Cliente.objects.order_by("nombre").values_list(
                    "nombre", "pais", "tipo_identificador_nacional", "identificador_nacional"
                )
            ),
            [("Ana", "CL", "rut", "12345678-5"), ("Lucia", "VE", None, None)],
        )

    def test_tipo_numero_y_pais_van_juntos(self):
        sin_numero = self.errores(self.crear(national_id_country="CL", national_id_type="rut"))
        self.assertEqual(sin_numero["id_national_id"], "Escribe el identificador nacional del tipo elegido.")
        sin_tipo = self.errores(self.crear(national_id="12345678-5"))
        self.assertEqual(sin_tipo["id_national_id_type"], "Elige el tipo de identificador nacional.")
        self.assertEqual(sin_tipo["id_national_id_country"], "Elige el país del identificador nacional.")
        mal_numero = self.errores(
            self.crear(national_id_country="CL", national_id_type="rut", national_id="12.345.678-9")
        )
        self.assertIn("dígito verificador", mal_numero["id_national_id"])
        self.assertFalse(Cliente.objects.exists())

    def test_las_reglas_de_los_nombres(self):
        errores = self.errores(self.crear(first_name="", second_surname="Pérez"))
        self.assertIn("id_first_name", errores)
        self.assertEqual(errores["id_first_surname"], "Escribe el primer apellido antes del segundo.")

    def test_editar_carga_los_datos_y_permite_vaciar_el_identificador(self):
        cliente = Cliente.objects.create(
            nombre="Carla Andrea",
            apellido="Rojas",
            pais="MX",
            tipo_identificador_nacional="curp",
            identificador_nacional="BOXW310820HNERXN09",
        )
        html = self.navegador.get(
            reverse("client_detail_modal", kwargs={"pk": cliente.pk}),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        ).content.decode()
        self.assertRegex(html, r'name="first_name" value="Carla"')
        self.assertRegex(html, r'name="second_name" value="Andrea"')
        self.assertRegex(html, r'<option value="curp" selected>CURP</option>')
        respuesta = self.editar(cliente, first_name="Carla", first_surname="Soto")
        self.assertEqual(respuesta.status_code, 200)
        cliente.refresh_from_db()
        self.assertEqual(
            (cliente.nombre, cliente.apellido, cliente.pais, cliente.identificador_nacional),
            ("Carla", "Soto", None, None),
        )

    def test_identificador_correo_y_telefono_no_se_repiten_entre_clientes(self):
        Cliente.objects.create(
            nombre="Otra",
            email="ana@correo.cl",
            telefono="+56912345678",
            pais="CL",
            tipo_identificador_nacional="rut",
            identificador_nacional="12345678-5",
        )
        errores = self.errores(
            self.crear(
                email="ANA@correo.cl",
                phone="9 1234 5678",
                national_id_country="CL",
                national_id_type="rut",
                national_id="12.345.678-5",
            )
        )
        self.assertEqual(errores["id_email"], "Ese correo ya lo usa otro cliente.")
        self.assertEqual(errores["id_phone"], "Ese teléfono ya lo usa otro cliente.")
        self.assertEqual(
            errores["id_national_id"], "Ese identificador nacional ya lo tiene otro cliente."
        )

    def test_editar_conserva_sus_datos_y_un_cliente_borrado_no_bloquea(self):
        cliente = Cliente.objects.create(
            nombre="Ana", email="ana@correo.cl", telefono="+56912345678"
        )
        respuesta = self.editar(cliente, email="ana@correo.cl", phone="912345678")
        self.assertEqual(respuesta.status_code, 200)
        cliente.delete()
        self.assertEqual(self.crear(email="ana@correo.cl", phone="912345678").status_code, 200)
