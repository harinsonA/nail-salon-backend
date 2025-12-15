from datetime import date, time
from decimal import Decimal
from result import Ok, Err, Result

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.clients.models import Cliente
from apps.services.models import Servicio


class HandlerAgenda:
    def __init__(self, clients_ids: list, services_ids: list):
        self.clients = self.__get_clients(clients_ids)
        self.services = self.__get_services(services_ids)

    @staticmethod
    def __get_clients(clients_ids: list) -> list:
        return Cliente.activos.filter(id__in=clients_ids).in_bulk()

    @staticmethod
    def __get_services(services_ids: list) -> list:
        return Servicio.activos.filter(id__in=services_ids).in_bulk()

    @staticmethod
    def __parse_date(service: str) -> date:
        day, month, year = service.get("fecha", "01/01/2000").split("/")
        return date(year=int(year), month=int(month), day=int(day))

    @staticmethod
    def __parse_time(service: str) -> time:
        hour, minute = service.get("hora", "00:00").split(":")
        return time(hour=int(hour), minute=int(minute))

    def __get_agenda_instance(self, client_id: int, service: dict) -> Cita:
        return Cita(
            cliente=self.clients.get(client_id),
            fecha_agenda=self.__parse_date(service),
            hora_agenda=self.__parse_time(service),
            estado=Cita.EstadoChoices.PENDIENTE,
        )

    def __get_agenda_detail_instance(
        self, agenda_instance: Cita, service: dict
    ) -> DetalleCita:
        return DetalleCita(
            cita=agenda_instance,
            servicio=self.services.get(service.get("id")),
            precio_acordado=Decimal(f"{service.get('total', 0)}"),
            cantidad_servicios=service.get("cantidad", 1),
            notas_detalle=service.get("observaciones", ""),
            descuento=Decimal(f"{service.get('descuento', 0)}"),
        )

    def group_agendas_by_date(self, agendas: list) -> list:
        services_grouped_by_date = {}
        for agenda in agendas:
            client_id = agenda.get("idCliente")
            services = agenda.get("servicios", [])
            if not client_id or not services:
                continue
            client_id = int(client_id)

            for service in services:
                service_date = service.get("fecha")
                if not service_date:
                    continue
                date_id = service_date.replace("/", "_")
                date_id += f"_{service.get('hora', '00:00').replace(':', '_')}"
                if date_id not in services_grouped_by_date:
                    services_grouped_by_date = {
                        **services_grouped_by_date,
                        date_id: {},
                    }

                if client_id not in services_grouped_by_date[date_id]:
                    services_grouped_by_date[date_id] = {
                        **services_grouped_by_date[date_id],
                        client_id: {
                            "cita": self.__get_agenda_instance(client_id, service),
                            "detalle_servicios": [],
                        },
                    }
                agenda_instance = services_grouped_by_date[date_id][client_id]["cita"]
                services_grouped_by_date[date_id][client_id][
                    "detalle_servicios"
                ].append(self.__get_agenda_detail_instance(agenda_instance, service))
        return services_grouped_by_date

    @staticmethod
    def __save(clients_agendas) -> None:
        for __, agenda_details in clients_agendas.items():
            cita_instance = agenda_details.get("cita")
            cita_instance.save()
            for detalle in agenda_details.get("detalle_servicios", []):
                detalle.cita = cita_instance
                detalle.save()

    def create(self, agendas: list) -> Result[str, str]:
        if not agendas:
            return Err("Sin agendas para procesar.")
        agenda_grouped_by_date = self.group_agendas_by_date(agendas)
        for __, clients_agendas in agenda_grouped_by_date.items():
            self.__save(clients_agendas)
        return Ok("Agendas procesadas correctamente.")


class HandlerAgendaList:
    @staticmethod
    def __get_date_formatted(**kwargs) -> str:
        fecha_agenda = kwargs.get("fecha_agenda")
        if not fecha_agenda:
            return "--"
        day = fecha_agenda.strftime("%d")
        weekdays = [
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            "sábado",
            "domingo",
        ]
        weekday_name = weekdays[fecha_agenda.weekday()].capitalize()
        return f"{day} - {weekday_name}"

    @staticmethod
    def __get_client_full_name(**kwargs) -> str:
        first_name = kwargs.get("cliente__nombre", "")
        last_name = kwargs.get("cliente__apellido", "")
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_formatted_time(**kwargs) -> str:
        hora_agenda = kwargs.get("hora_agenda")
        if not hora_agenda:
            return "--:--"
        return hora_agenda.strftime("%H:%M")

    def __get_agendas_grouped_by_date(self, values: list) -> dict:
        agendas_by_date = {}
        for agenda in values:
            date_id = agenda.get("fecha_agenda").strftime("%Y_%m_%d")
            if date_id not in agendas_by_date:
                agendas_by_date[date_id] = {
                    "pk": date_id,
                    "date": self.__get_date_formatted(**agenda),
                    "agendas": [],
                }
            agendas_by_date[date_id]["agendas"].append(
                {
                    **agenda,
                    "cliente_full_name": self.__get_client_full_name(**agenda),
                    "formatted_time": self.__get_formatted_time(**agenda),
                }
            )
        return [agenda for agenda in agendas_by_date.values()]

    def get_data(self, values: list) -> list:
        return self.__get_agendas_grouped_by_date(values)
