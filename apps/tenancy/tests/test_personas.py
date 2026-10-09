from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.tenancy.models import Negocio, Persona, PersonaCorreo, PersonaDireccion, PersonaTelefono


class PersonaCorreoTests(TestCase):
    def setUp(self):
        self.persona = Persona.objects.create(nombres="Carlos", apellidos="Rojas")

    def test_el_correo_se_guarda_en_minusculas(self):
        correo = PersonaCorreo.objects.create(persona=self.persona, correo="  Carlos@ElCorte.cl ")
        correo.refresh_from_db()
        self.assertEqual(correo.correo, "carlos@elcorte.cl")

    def test_la_base_rechaza_correos_con_mayusculas(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PersonaCorreo.objects.bulk_create([PersonaCorreo(persona=self.persona, correo="Carlos@ElCorte.cl")])

    def test_la_misma_persona_no_repite_correo(self):
        PersonaCorreo.objects.create(persona=self.persona, correo="carlos@elcorte.cl")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PersonaCorreo.objects.create(persona=self.persona, correo="CARLOS@elcorte.cl")

    def test_dos_personas_pueden_compartir_correo(self):
        otra = Persona.objects.create(nombres="Ana")
        PersonaCorreo.objects.create(persona=self.persona, correo="local@elcorte.cl")
        PersonaCorreo.objects.create(persona=otra, correo="local@elcorte.cl")
        self.assertEqual(PersonaCorreo.objects.filter(correo="local@elcorte.cl").count(), 2)


class PrincipalUnicoTests(TestCase):
    def setUp(self):
        self.persona = Persona.objects.create(nombres="Carlos")

    def test_marcar_un_principal_desmarca_el_anterior(self):
        primero = PersonaCorreo.objects.create(persona=self.persona, correo="a@correo.cl", es_principal=True)
        segundo = PersonaCorreo.objects.create(persona=self.persona, correo="b@correo.cl", es_principal=True)
        primero.refresh_from_db()
        self.assertFalse(primero.es_principal)
        self.assertTrue(segundo.es_principal)
        self.assertFalse(primero.history.first().es_principal)

    def test_la_base_rechaza_dos_principales(self):
        PersonaTelefono.objects.create(persona=self.persona, numero="912345678", es_principal=True)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PersonaTelefono.objects.bulk_create(
                [PersonaTelefono(persona=self.persona, numero="987654321", es_principal=True)]
            )

    def test_el_principal_es_por_persona(self):
        otra = Persona.objects.create(nombres="Ana")
        PersonaDireccion.objects.create(persona=self.persona, calle="Av. Uno", es_principal=True)
        PersonaDireccion.objects.create(persona=otra, calle="Av. Dos", es_principal=True)
        self.assertEqual(PersonaDireccion.objects.filter(es_principal=True).count(), 2)


class PersonaTelefonoTests(TestCase):
    def setUp(self):
        self.persona = Persona.objects.create(nombres="Carlos")

    def test_valida_el_movil_segun_el_pais(self):
        PersonaTelefono(persona=self.persona, numero="912345678").full_clean()
        with self.assertRaises(ValidationError) as error:
            PersonaTelefono(persona=self.persona, numero="812345678").full_clean()
        self.assertIn("numero", error.exception.message_dict)

    def test_el_fijo_solo_exige_digitos(self):
        PersonaTelefono(persona=self.persona, numero="223456789", tipo=PersonaTelefono.Tipo.FIJO).full_clean()
        with self.assertRaises(ValidationError):
            PersonaTelefono(persona=self.persona, numero="22 345-6789", tipo=PersonaTelefono.Tipo.FIJO).full_clean()

    def test_la_misma_persona_no_repite_numero(self):
        PersonaTelefono.objects.create(persona=self.persona, numero="912345678")
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PersonaTelefono.objects.create(persona=self.persona, numero="912345678")


class PersonaDireccionTests(TestCase):
    def setUp(self):
        self.persona = Persona.objects.create(nombres="Carlos")

    def test_las_coordenadas_van_juntas(self):
        with transaction.atomic(), self.assertRaises(IntegrityError):
            PersonaDireccion.objects.create(persona=self.persona, calle="Av. Uno", latitud="-33.4489")

    def test_valida_el_rango_de_las_coordenadas_y_el_pais(self):
        PersonaDireccion(persona=self.persona, calle="Av. Uno", latitud="-33.448900", longitud="-70.669300").full_clean()
        with self.assertRaises(ValidationError) as error:
            PersonaDireccion(persona=self.persona, calle="Av. Uno", latitud="-95", longitud="200", pais="cl").full_clean()
        self.assertEqual(set(error.exception.message_dict), {"latitud", "longitud", "pais"})


class BorrarPersonaTests(TestCase):
    def setUp(self):
        self.persona = Persona.objects.create(nombres="Carlos")
        PersonaCorreo.objects.create(persona=self.persona, correo="carlos@elcorte.cl")
        PersonaTelefono.objects.create(persona=self.persona, numero="912345678")
        PersonaDireccion.objects.create(persona=self.persona, calle="Av. Uno")

    def test_el_borrado_normal_es_logico(self):
        self.persona.delete()
        self.assertFalse(Persona.objects.filter(pk=self.persona.pk).exists())
        self.assertTrue(Persona.all_objects.filter(pk=self.persona.pk).exists())

    def test_el_borrado_definitivo_se_lleva_sus_contactos(self):
        self.persona.delete(soft=False)
        self.assertFalse(PersonaCorreo.objects.exists())
        self.assertFalse(PersonaTelefono.objects.exists())
        self.assertFalse(PersonaDireccion.objects.exists())

    def test_no_se_borra_a_quien_es_titular(self):
        Negocio.objects.create(schema_name="el_corte", nombre="Barbería El Corte", titular=self.persona)
        for soft in (True, False):
            with self.subTest(soft=soft), self.assertRaises(ProtectedError):
                self.persona.delete(soft=soft)
        self.assertTrue(Persona.objects.filter(pk=self.persona.pk).exists())
