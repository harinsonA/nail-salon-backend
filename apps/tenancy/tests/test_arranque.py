from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import schema_context

from apps.profiles.models import Perfil
from apps.tenancy.esquemas import clasificar_negocios
from apps.tenancy.models import Negocio, Persona
from apps.tenancy.tasks import preparar_negocio
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()


class ArranqueConAltasAMediasTests(NegocioTestCase):
    esquema = "arranque"

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.ACTIVO)
        titular = Persona.objects.create(nombres="X")
        Negocio.objects.create(schema_name="a_medias", nombre="A medias", titular=titular)
        Negocio.objects.create(schema_name="sin_esquema", nombre="Sin esquema", titular=titular, estado=Negocio.Estado.ACTIVO)

    def test_solo_los_negocios_listos_se_tocan_al_arrancar(self):
        listos, omitidos = clasificar_negocios()
        self.assertIn("arranque", listos)
        self.assertIn("a_medias", omitidos)
        self.assertIn("sin_esquema", omitidos)

    def test_migrar_esquemas_no_se_cae_por_un_alta_a_medias(self):
        salida = StringIO()
        call_command("migrar_esquemas", verbosity=0, stdout=salida)
        self.assertIn("Se omite «a_medias»", salida.getvalue())
        self.assertIn("Se omite «sin_esquema»", salida.getvalue())

    def test_limpiar_sesiones_no_se_cae_por_un_alta_a_medias(self):
        salida = StringIO()
        call_command("limpiar_sesiones", stdout=salida)
        self.assertIn("Sesiones vencidas borradas", salida.getvalue())

    def test_la_tarea_de_alta_se_puede_reintentar_con_el_esquema_ya_creado(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        preparar_negocio(self.negocio.pk, "dueno@correo.cl", None)
        negocio = Negocio.objects.get(pk=self.negocio.pk)
        self.assertEqual(negocio.estado, Negocio.Estado.ACTIVO)
        with schema_context(self.esquema):
            propietario = User.objects.get(email="dueno@correo.cl")
            self.assertFalse(propietario.has_usable_password())
            self.assertEqual(propietario.perfil.rol, Perfil.Rol.PROPIETARIO)
