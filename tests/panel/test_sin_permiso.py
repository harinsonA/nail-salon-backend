from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()


class SinPermisoEnElPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def test_una_accion_reservada_muestra_la_pagina_del_panel(self):
        connection.set_schema_to_public()
        panel = Client(HTTP_HOST="admin.localhost")
        panel.force_login(self.staff)
        alta = reverse("admin:tenancy_negocio_alta", urlconf=settings.PUBLIC_SCHEMA_URLCONF)
        respuesta = panel.get(alta)
        self.assertContains(respuesta, "No tienes permiso para esta acción del panel.", status_code=403)
        self.assertContains(respuesta, 'href="/admin/"', status_code=403)
