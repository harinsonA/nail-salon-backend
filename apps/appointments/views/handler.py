from apps.appointments.models.agenda import Cita
from apps.clients.models import Cliente
from apps.services.models import Servicio


class Agenda:
    def __init__(self, clients_id: list, services_id: list):
        self.clients = self.__get_clients(clients_id)
        self.services = self.__get_services(services_id)

    @staticmethod
    def __get_clients(clients_id: list) -> list:
        return Cliente.objects.filter(
            id__in=clients_id, estado=Cliente.EstadoChoices.ACTIVO, is_removed=False
        ).in_bulk()

    @staticmethod
    def __get_services(services_id: list) -> list:
        return Servicio.objects.filter(
            id__in=services_id, estado=Servicio.EstadoChoices.ACTIVO, is_removed=False
        ).in_bulk()

    @staticmethod
    def __cleaned_agenda_data(agenda_data: dict) -> dict:
        pass

    def create_agendas(self, agendas_data: list) -> list:
        pass
