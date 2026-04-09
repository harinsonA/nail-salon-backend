from datetime import date, time
from decimal import Decimal
from django.urls import reverse_lazy
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
        servicio = self.services.get(service.get("id"))
        return DetalleCita(
            cita=agenda_instance,
            servicio=servicio,
            nombre_servicio=servicio.nombre,
            precio_servicio=servicio.precio,
            duracion_estimada_servicio=servicio.duracion_estimada,
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
    def get_client_full_name(**kwargs) -> str:
        first_name = kwargs.get("cliente__nombre", "")
        last_name = kwargs.get("cliente__apellido", "")
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def get_formatted_time(**kwargs) -> str:
        hora_agenda = kwargs.get("hora_agenda")
        if not hora_agenda:
            return "--:--"
        return hora_agenda.strftime("%H:%M")

    @staticmethod
    def get_options(agenda_id, agenda_status) -> dict:
        options = {}
        if agenda_status == Cita.EstadoChoices.PENDIENTE:
            options["options"] = {
                "agenda_update_modal_url": reverse_lazy(
                    "agenda_update_modal", args=[agenda_id]
                ),
                "agenda_cancel_modal_url": reverse_lazy(
                    "agenda_cancel_modal", args=[agenda_id]
                ),
                "agenda_delete_modal_url": reverse_lazy(
                    "agenda_delete_modal", args=[agenda_id]
                ),
                "agenda_confirmation_modal_url": reverse_lazy(
                    "agenda_confirmation_modal", args=[agenda_id]
                ),
            }
            return options
        if agenda_status == Cita.EstadoChoices.COMPLETADA:
            options["options"] = {
                "is_agenda_completed": True,
            }
            return options
        if agenda_status == Cita.EstadoChoices.CANCELADA:
            options["options"] = {
                "agenda_restore_modal_url": reverse_lazy(
                    "agenda_restore_modal", args=[agenda_id]
                ),
                "agenda_delete_modal_url": reverse_lazy(
                    "agenda_delete_modal", args=[agenda_id]
                ),
            }
            return options
        return options
