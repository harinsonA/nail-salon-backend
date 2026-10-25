from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase

from apps.panel.models import PerfilPanel

User = get_user_model()


class PerfilPanelTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()

    def test_guarda_el_identificador_nacional_del_usuario_del_panel(self):
        usuario = User.objects.create_user(username="soporte", password="x", is_staff=True)
        perfil = PerfilPanel.objects.create(
            user=usuario,
            pais="CL",
            tipo_identificador_nacional="rut",
            identificador_nacional="12345678-5",
        )
        self.assertEqual(usuario.perfil_panel, perfil)
        self.assertEqual(perfil.history.count(), 1)

    def test_los_campos_empiezan_vacios_y_hay_uno_por_usuario(self):
        usuario = User.objects.create_user(username="soporte", password="x", is_staff=True)
        perfil = PerfilPanel.objects.create(user=usuario)
        self.assertEqual(
            (perfil.pais, perfil.tipo_identificador_nacional, perfil.identificador_nacional),
            (None, None, None),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            PerfilPanel.objects.create(user=usuario)
