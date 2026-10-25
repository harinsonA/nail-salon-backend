from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.profiles.permisos import puede_gestionar
from tests.base import IDENTIFICADOR_VALIDO, NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class EquipoTests(NegocioTestCase):
    esquema = "equipo"
    dominio = "equipo.localhost"

    def crear(self, rol, nombre=None):
        nombre = nombre or rol
        usuario = User.objects.create_user(username=nombre, email=f"{nombre}@correo.cl", password="x")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.select_related("perfil").get(pk=usuario.pk)

    def navegador_de(self, usuario):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def errores(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        return {error["id_element"] for error in respuesta.json()["errors"]}

    def filas(self, navegador, **filtros):
        respuesta = navegador.get(reverse("equipo_lista"), filtros)
        self.assertEqual(respuesta.status_code, 200)
        return {fila["email"]: fila for fila in respuesta.json()["data"]}

    def enlaces(self, fila):
        return [opcion["link"] for opcion in fila["options"]]

    def test_quien_gestiona_a_quien(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        encargada = self.crear(Rol.ENCARGADO, "ana")
        otra_encargada = self.crear(Rol.ENCARGADO, "sofi")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        self.assertTrue(puede_gestionar(propietaria, encargada))
        self.assertTrue(puede_gestionar(propietaria, colaboradora))
        self.assertTrue(puede_gestionar(encargada, colaboradora))
        self.assertFalse(puede_gestionar(encargada, otra_encargada))
        self.assertFalse(puede_gestionar(encargada, propietaria))
        self.assertFalse(puede_gestionar(propietaria, propietaria))
        self.assertFalse(puede_gestionar(colaboradora, colaboradora))

    def test_la_lista_muestra_acciones_solo_sobre_quien_se_puede_gestionar(self):
        encargada = self.crear(Rol.ENCARGADO, "ana")
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(encargada)
        lista = navegador.get(reverse("equipo"))
        self.assertEqual(lista.status_code, 200)
        self.assertContains(lista, reverse("equipo_lista"))
        filas = self.filas(navegador)
        self.assertEqual(
            self.enlaces(filas[colaboradora.email]),
            [
                reverse("equipo_editar", args=[colaboradora.pk]),
                reverse("equipo_restablecer_clave", args=[colaboradora.pk]),
                reverse("equipo_activar", args=[colaboradora.pk]),
            ],
        )
        self.assertEqual(filas[propietaria.email]["options"], [])
        self.assertEqual(filas[encargada.email]["options"], [])

    def test_la_lista_trae_rol_estado_y_contadores(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        User.objects.filter(pk=colaboradora.pk).update(is_active=False)
        respuesta = self.navegador_de(propietaria).get(reverse("equipo_lista"))
        datos = respuesta.json()
        self.assertEqual((datos["active_members"], datos["inactive_members"], datos["locked_members"]), (1, 1, 0))
        fila = {fila["email"]: fila for fila in datos["data"]}[colaboradora.email]
        self.assertEqual(fila["role_label"], "Colaborador")
        self.assertFalse(fila["is_active"])
        self.assertEqual(fila["options"][-1]["label"], "Reactivar")

    def test_la_lista_filtra_por_estado_y_rol(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        encargada = self.crear(Rol.ENCARGADO, "ana")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        User.objects.filter(pk=colaboradora.pk).update(is_active=False)
        navegador = self.navegador_de(propietaria)
        self.assertEqual(set(self.filas(navegador)), {propietaria.email, encargada.email, colaboradora.email})
        self.assertEqual(set(self.filas(navegador, status="inactive")), {colaboradora.email})
        self.assertEqual(set(self.filas(navegador, status="active", role=Rol.ENCARGADO)), {encargada.email})
        self.assertEqual(set(self.filas(navegador, **{"search[value]": "lau"})), {colaboradora.email})

    def test_la_lista_abre_el_modal_de_crear(self):
        lista = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria")).get(reverse("equipo"))
        self.assertContains(lista, f'data-form-url="{reverse("equipo_crear")}"')
        self.assertContains(lista, "Los miembros no se borran")

    def test_la_propietaria_crea_un_encargado_con_clave_temporal(self):
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        modal = navegador.get(reverse("equipo_crear"))
        self.assertContains(modal, "Nuevo miembro")
        self.assertContains(modal, "data-sensitive")
        respuesta = navegador.post(
            reverse("equipo_crear"),
            {**IDENTIFICADOR_VALIDO, "first_name": "Ana", "last_name": "Pérez", "email": "Ana@Correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("no-store", respuesta["Cache-Control"])
        datos = respuesta.json()
        self.assertEqual(datos["email"], "ana@correo.cl")
        nueva = User.objects.get(email="ana@correo.cl")
        self.assertEqual(nueva.username, "ana@correo.cl")
        self.assertEqual(nueva.perfil.rol, Rol.ENCARGADO)
        self.assertTrue(nueva.perfil.debe_cambiar_clave)
        self.assertTrue(nueva.check_password(datos["password"]))

    def test_la_encargada_solo_crea_colaboradores(self):
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        formulario = navegador.get(reverse("equipo_crear"))
        self.assertEqual([valor for valor, _ in formulario.context["form"].fields["rol"].choices], [Rol.COLABORADOR])
        intento = navegador.post(
            reverse("equipo_crear"),
            {**IDENTIFICADOR_VALIDO, "first_name": "Sofi", "email": "sofi@correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertEqual(self.errores(intento), {"id_rol"})
        self.assertFalse(User.objects.filter(email="sofi@correo.cl").exists())

    def test_no_se_repite_un_correo(self):
        self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        respuesta = navegador.post(
            reverse("equipo_crear"),
            {**IDENTIFICADOR_VALIDO, "first_name": "Laura", "email": "LAURA@correo.cl", "rol": Rol.COLABORADOR},
        )
        self.assertEqual(self.errores(respuesta), {"id_email"})

    def test_el_nombre_solo_acepta_letras(self):
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        respuesta = navegador.post(
            reverse("equipo_crear"),
            {**IDENTIFICADOR_VALIDO, "first_name": "Ana123", "email": "ana@correo.cl", "rol": Rol.COLABORADOR},
        )
        self.assertEqual(self.errores(respuesta), {"id_first_name"})

    def test_editar_usa_el_mismo_formulario_con_sus_datos(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        User.objects.filter(pk=colaboradora.pk).update(first_name="Laura", last_name="Soto")
        modal = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria")).get(
            reverse("equipo_editar", args=[colaboradora.pk])
        )
        self.assertContains(modal, "Editar miembro · Laura Soto")
        self.assertNotContains(modal, "data-sensitive")
        self.assertEqual(
            modal.context["form"].initial,
            {
                "national_id_country": "",
                "national_id_type": "",
                "national_id": "",
                "first_name": "Laura",
                "last_name": "Soto",
                "email": "laura@correo.cl",
                "rol": Rol.COLABORADOR,
            },
        )

    def test_la_propietaria_edita_datos_y_rol(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        respuesta = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria")).post(
            reverse("equipo_editar", args=[colaboradora.pk]),
            {**IDENTIFICADOR_VALIDO, "first_name": "Laura", "last_name": "Soto", "email": "Laura.Soto@correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertEqual(respuesta.json()["message"], "Laura Soto quedó actualizado.")
        colaboradora.refresh_from_db()
        colaboradora.perfil.refresh_from_db()
        self.assertEqual(
            (colaboradora.get_full_name(), colaboradora.email, colaboradora.username, colaboradora.perfil.rol),
            ("Laura Soto", "laura.soto@correo.cl", "laura.soto@correo.cl", Rol.ENCARGADO),
        )
        self.assertTrue(colaboradora.check_password("x"))
        self.assertEqual(colaboradora.perfil.history.first().rol, Rol.ENCARGADO)

    def test_editar_conserva_su_propio_correo_y_rechaza_uno_ajeno(self):
        self.crear(Rol.COLABORADOR, "sofi")
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        ruta = reverse("equipo_editar", args=[colaboradora.pk])
        mismo = navegador.post(ruta, {**IDENTIFICADOR_VALIDO, "first_name": "Laura", "email": "laura@correo.cl", "rol": Rol.COLABORADOR})
        self.assertEqual(mismo.status_code, 200)
        ajeno = navegador.post(ruta, {**IDENTIFICADOR_VALIDO, "first_name": "Laura", "email": "sofi@correo.cl", "rol": Rol.COLABORADOR})
        self.assertEqual(self.errores(ajeno), {"id_email"})
        ascenso = navegador.post(ruta, {**IDENTIFICADOR_VALIDO, "first_name": "Laura", "email": "laura@correo.cl", "rol": Rol.ENCARGADO})
        self.assertEqual(self.errores(ascenso), {"id_rol"})

    def test_desactivar_y_reactivar(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        modal = navegador.get(reverse("equipo_activar", args=[colaboradora.pk]))
        self.assertContains(modal, "Desactivar miembro")
        respuesta = navegador.post(reverse("equipo_activar", args=[colaboradora.pk]))
        self.assertEqual(respuesta.json()["message"], "laura@correo.cl quedó desactivado.")
        colaboradora.refresh_from_db()
        self.assertFalse(colaboradora.is_active)
        sesion_de_laura = self.navegador_de(colaboradora)
        self.assertRedirects(
            sesion_de_laura.get(reverse("calendar")), f"{reverse('login')}?next={reverse('calendar')}",
            fetch_redirect_response=False,
        )
        navegador.post(reverse("equipo_activar", args=[colaboradora.pk]))
        colaboradora.refresh_from_db()
        self.assertTrue(colaboradora.is_active)

    def test_restablecer_la_clave_de_un_colaborador(self):
        colaboradora = self.crear(Rol.COLABORADOR, "laura")
        navegador = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        modal = navegador.get(reverse("equipo_restablecer_clave", args=[colaboradora.pk]))
        self.assertContains(modal, "data-sensitive")
        respuesta = navegador.post(reverse("equipo_restablecer_clave", args=[colaboradora.pk]))
        self.assertIn("no-store", respuesta["Cache-Control"])
        datos = respuesta.json()
        self.assertEqual(datos["email"], colaboradora.email)
        colaboradora.refresh_from_db()
        self.assertTrue(colaboradora.check_password(datos["password"]))
        self.assertTrue(colaboradora.perfil.debe_cambiar_clave)

    def test_nadie_del_negocio_toca_a_la_propietaria_ni_la_encargada_a_otra(self):
        propietaria = self.crear(Rol.PROPIETARIO, "maria")
        otra_encargada = self.crear(Rol.ENCARGADO, "sofi")
        encargada = self.navegador_de(self.crear(Rol.ENCARGADO, "ana"))
        for objetivo in (propietaria, otra_encargada):
            for ruta in ("equipo_editar", "equipo_activar", "equipo_restablecer_clave", "equipo_desbloquear"):
                with self.subTest(objetivo=objetivo.username, ruta=ruta):
                    self.assertEqual(encargada.get(reverse(ruta, args=[objetivo.pk])).status_code, 403)
                    self.assertEqual(encargada.post(reverse(ruta, args=[objetivo.pk])).status_code, 403)
        propia = self.navegador_de(propietaria)
        self.assertEqual(propia.post(reverse("equipo_activar", args=[propietaria.pk])).status_code, 403)
        propietaria.refresh_from_db()
        self.assertTrue(propietaria.is_active)
        self.assertTrue(propietaria.check_password("x"))

    def test_el_colaborador_no_entra_al_equipo(self):
        navegador = self.navegador_de(self.crear(Rol.COLABORADOR, "laura"))
        self.assertEqual(navegador.get(reverse("equipo")).status_code, 403)
        self.assertEqual(navegador.get(reverse("equipo_lista")).status_code, 403)
        self.assertEqual(navegador.get(reverse("equipo_crear")).status_code, 403)
        self.assertNotContains(navegador.get(reverse("calendar")), f'href="{reverse("equipo")}"')

    def test_el_identificador_nacional_es_obligatorio_y_se_guarda_en_su_perfil(self):
        navegador = self.navegador_de(self.crear(Rol.PROPIETARIO, "maria"))
        sin_identificador = navegador.post(
            reverse("equipo_crear"),
            {"first_name": "Ana", "email": "ana@correo.cl", "rol": Rol.ENCARGADO},
        )
        self.assertTrue(
            {"id_national_id_country", "id_national_id_type", "id_national_id"}
            <= self.errores(sin_identificador)
        )
        navegador.post(
            reverse("equipo_crear"),
            {
                "national_id_country": "PE",
                "national_id_type": "dni",
                "national_id": "01234567",
                "first_name": "Ana",
                "email": "ana@correo.cl",
                "rol": Rol.ENCARGADO,
            },
        )
        perfil = Perfil.objects.get(user__email="ana@correo.cl")
        self.assertEqual(
            (perfil.rol, perfil.pais, perfil.tipo_identificador_nacional, perfil.identificador_nacional),
            (Rol.ENCARGADO, "PE", "dni", "01234567"),
        )
        modal = navegador.get(reverse("equipo_editar", args=[perfil.user.pk]))
        self.assertContains(modal, '<option value="dni" selected>DNI</option>')
