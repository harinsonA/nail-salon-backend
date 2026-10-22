from django.urls import reverse_lazy

from apps.appointments.models.agenda import Cita


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
