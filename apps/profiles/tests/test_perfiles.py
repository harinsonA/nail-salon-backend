from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.profiles.models import Perfil, PerfilDireccion, PerfilTelefono
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()


class PerfilTests(NegocioTestCase):
    def crear_perfil(self, username, **datos):
        usuario = User.objects.create_user(username=username, email=f"{username}@correo.cl")
        return Perfil.objects.create(user=usuario, **datos)

    def test_valores_por_defecto(self):
        perfil = self.crear_perfil("ana")
        self.assertEqual(perfil.rol, Perfil.Rol.COLABORADOR)
        self.assertTrue(perfil.debe_cambiar_clave)
        self.assertEqual(perfil.user.perfil, perfil)

    def test_un_solo_propietario_por_negocio(self):
        self.crear_perfil("maria", rol=Perfil.Rol.PROPIETARIO)
        self.crear_perfil("ana", rol=Perfil.Rol.ENCARGADO)
        self.crear_perfil("sofi", rol=Perfil.Rol.ENCARGADO)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.crear_perfil("otra", rol=Perfil.Rol.PROPIETARIO)

    def test_el_cambio_de_rol_queda_en_el_historial(self):
        perfil = self.crear_perfil("ana")
        perfil.rol = Perfil.Rol.ENCARGADO
        perfil.save()
        self.assertEqual(
            list(perfil.history.values_list("rol", flat=True)),
            [Perfil.Rol.ENCARGADO, Perfil.Rol.COLABORADOR],
        )

    def test_hasta_dos_telefonos_por_usuario(self):
        perfil = self.crear_perfil("ana")
        PerfilTelefono.objects.create(perfil=perfil, numero="912345678", es_principal=True)
        PerfilTelefono.objects.create(perfil=perfil, numero="987654321")
        with self.assertRaises(ValidationError):
            PerfilTelefono(perfil=perfil, numero="955555555").full_clean()
        segundo = perfil.telefonos.get(numero="987654321")
        segundo.numero = "955555555"
        segundo.full_clean()

    def test_una_direccion_principal_por_usuario(self):
        perfil = self.crear_perfil("ana")
        primera = PerfilDireccion.objects.create(perfil=perfil, calle="Av. Uno", es_principal=True)
        PerfilDireccion.objects.create(perfil=perfil, calle="Av. Dos", es_principal=True)
        primera.refresh_from_db()
        self.assertFalse(primera.es_principal)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PerfilDireccion.objects.bulk_create([PerfilDireccion(perfil=perfil, calle="Av. Tres", es_principal=True)])

    def test_borrar_el_usuario_borra_su_perfil_y_contactos(self):
        perfil = self.crear_perfil("ana")
        PerfilTelefono.objects.create(perfil=perfil, numero="912345678")
        PerfilDireccion.objects.create(perfil=perfil, calle="Av. Uno")
        perfil.user.delete()
        self.assertFalse(Perfil.objects.exists())
        self.assertFalse(PerfilTelefono.objects.exists())
        self.assertFalse(PerfilDireccion.objects.exists())

    def test_las_tablas_del_equipo_viven_solo_en_el_negocio(self):
        tablas = (
            "perfiles",
            "perfiles_historial",
            "perfiles_telefonos",
            "perfiles_telefonos_historial",
            "perfiles_direcciones",
            "perfiles_direcciones_historial",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, table_schema FROM information_schema.tables WHERE table_name = ANY(%s)",
                [list(tablas)],
            )
            encontradas = cursor.fetchall()
        self.assertCountEqual(encontradas, [(tabla, self.esquema) for tabla in tablas])
