from datetime import timedelta

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.common.models import ConPrincipal
from apps.tenancy.models import Negocio, NegocioDireccion, Persona, Rubro


class NegocioTests(TestCase):
    def setUp(self):
        self.titular = Persona.objects.create(nombres="Carlos")

    def crear(self, **datos):
        datos.setdefault("schema_name", "el_corte")
        datos.setdefault("nombre", "Barbería El Corte")
        datos.setdefault("titular", self.titular)
        return Negocio.objects.create(**datos)

    def test_valores_por_defecto(self):
        negocio = self.crear()
        self.assertEqual(negocio.estado, Negocio.Estado.PREPARANDO)
        self.assertEqual(negocio.zona_horaria, "America/Santiago")
        self.assertIsNotNone(negocio.estado_desde)

    def test_el_titular_es_obligatorio(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.crear(titular=None)

    def test_el_negocio_public_no_lleva_titular(self):
        negocio = self.crear(schema_name="public", nombre="Hi Agenda", titular=None)
        self.assertIsNone(negocio.titular)

    def test_estado_desde_cambia_solo_con_el_estado(self):
        negocio = self.crear()
        Negocio.objects.filter(pk=negocio.pk).update(estado_desde=timezone.now() - timedelta(days=30))
        negocio.refresh_from_db()
        antes = negocio.estado_desde
        negocio.nombre = "El Corte"
        negocio.save()
        self.assertEqual(negocio.estado_desde, antes)
        negocio.estado = Negocio.Estado.MOROSO
        negocio.save()
        self.assertGreater(negocio.estado_desde, antes)

    def test_cada_cambio_queda_en_el_historial(self):
        negocio = self.crear()
        negocio.estado = Negocio.Estado.ACTIVO
        negocio._change_reason = "Alta terminada"
        negocio.save()
        ultimo = negocio.history.first()
        self.assertEqual(negocio.history.count(), 2)
        self.assertEqual(ultimo.estado, Negocio.Estado.ACTIVO)
        self.assertEqual(ultimo.history_change_reason, "Alta terminada")

    def test_valida_zona_horaria_y_esquema(self):
        negocio = Negocio(schema_name="admin", nombre="X", titular=self.titular, zona_horaria="Marte/Olympus")
        with self.assertRaises(ValidationError) as error:
            negocio.full_clean()
        self.assertIn("zona_horaria", error.exception.message_dict)
        self.assertIn("__all__", error.exception.message_dict)

    def test_un_rubro_en_uso_no_se_borra(self):
        rubro = Rubro.objects.get(codigo="barberia")
        self.crear(rubro=rubro)
        with self.assertRaises(ProtectedError):
            rubro.delete()

    def test_una_sola_direccion_principal_por_negocio(self):
        negocio = self.crear()
        local = NegocioDireccion.objects.create(negocio=negocio, calle="Av. Uno", etiqueta="local", es_principal=True)
        NegocioDireccion.objects.create(negocio=negocio, calle="Av. Dos", etiqueta="sucursal", es_principal=True)
        local.refresh_from_db()
        self.assertFalse(local.es_principal)
        self.assertEqual(negocio.direcciones.filter(es_principal=True).count(), 1)


class RubrosInicialesTests(TestCase):
    def test_la_migracion_carga_los_rubros(self):
        self.assertEqual(
            list(Rubro.objects.values_list("codigo", flat=True)),
            ["unas", "barberia", "peluqueria", "estetica", "salud", "otro"],
        )


class MoldesTests(TestCase):
    def modelos_con_principal(self):
        return [modelo for modelo in apps.get_models() if issubclass(modelo, ConPrincipal)]

    def test_cada_lista_con_principal_tiene_su_indice_en_la_base(self):
        modelos = self.modelos_con_principal()
        self.assertGreaterEqual(len(modelos), 4)
        for modelo in modelos:
            with self.subTest(modelo=modelo.__name__):
                principales = [
                    restriccion
                    for restriccion in modelo._meta.constraints
                    if restriccion.name.endswith("_un_principal")
                ]
                self.assertEqual(len(principales), 1)
                self.assertEqual(principales[0].fields, (modelo.campo_dueno,))

    def test_las_tablas_de_historial_terminan_en_historial(self):
        with connection.cursor() as cursor:
            tablas = set(connection.introspection.table_names(cursor))
        for tabla in ("negocios", "personas", "personas_correos", "personas_telefonos",
                      "personas_direcciones", "negocios_direcciones"):
            with self.subTest(tabla=tabla):
                self.assertIn(f"{tabla}_historial", tablas)
