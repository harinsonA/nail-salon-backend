from datetime import date, time

from django.contrib.auth import get_user_model

from apps.appointments.calendar.query import CalendarQuery
from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()


class CalendarioBusquedaTests(NegocioTestCase):
    esquema = "calendario_busqueda"
    dominio = "calendario-busqueda.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=self.encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.encargada = User.objects.get(pk=self.encargada.pk)
        for nombre, apellido in [
            ("Verónica", "Saavedra"),
            ("Veronica", "Jara"),
            ("Bárbara", "Cárdenas"),
            ("Paula", "Peña"),
        ]:
            Cita.objects.create(
                cliente=Cliente.objects.create(nombre=nombre, apellido=apellido),
                fecha_agenda=date(2026, 10, 22),
                hora_agenda=time(10, 0),
            )

    def buscar(self, texto):
        citas = CalendarQuery(self.encargada, date(2026, 10, 19), date(2026, 10, 25), texto).appointments()
        return sorted(cita["cliente"] for cita in citas)

    def test_sin_tilde_encuentra_los_nombres_con_y_sin_tilde(self):
        self.assertEqual(self.buscar("veronica"), ["Veronica Jara", "Verónica Saavedra"])

    def test_con_tilde_tambien_encuentra_los_nombres_sin_tilde(self):
        self.assertEqual(self.buscar("Verónica"), ["Veronica Jara", "Verónica Saavedra"])

    def test_ignora_las_tildes_del_apellido_y_las_mayusculas(self):
        self.assertEqual(self.buscar("CARDENAS"), ["Bárbara Cárdenas"])

    def test_busca_por_nombre_y_apellido_juntos(self):
        self.assertEqual(self.buscar("barbara cardenas"), ["Bárbara Cárdenas"])

    def test_la_enie_sigue_siendo_distinta_de_la_ene(self):
        self.assertEqual(self.buscar("Peña"), ["Paula Peña"])
        self.assertEqual(self.buscar("Pena"), [])
