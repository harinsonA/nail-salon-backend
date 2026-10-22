from bootstrap_modal_forms.generic import BSModalReadView
from django.http import JsonResponse

from apps.appointments.models import Cita
from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME
from apps.common.views.base_views import ProtectedView

"""========================================================================="""
# region ........ Views


class AgendaDeleteModalView(ProtectedView, BSModalReadView):
    template_name = "common/delete_modal.html"
    model = Cita
    success_message = "Cita de %(client_full_name)s eliminada exitosamente."

    def get_object(self, queryset=None):
        agenda_id = self.kwargs.get("pk")
        return Cita.objects.filter(pk=agenda_id).first()

    @staticmethod
    def __get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_date_time_formatted(object_base) -> str:
        day = object_base.fecha_agenda.day
        month = MONTH_NUMBER_TO_NAME[object_base.fecha_agenda.month]
        year = object_base.fecha_agenda.year
        time = object_base.hora_agenda.strftime("%H:%M")
        return f"{day} de {month} de {year} a las {time}"

    def get_aditional_information(self, cita: Cita) -> list:
        date_time = self.__get_date_time_formatted(cita)
        additional_info = [
            {"text": f"Fecha cita: {date_time}", "icon": "event"},
        ]

        if cita.cliente.telefono:
            additional_info.append(
                {"text": f"Teléfono: {cita.cliente.telefono}", "icon": "phone"}
            )

        additional_info.extend(
            [
                {"text": f"Estado: {cita.get_estado_display()}", "icon": "info"},
                {"text": f"Servicios: {cita.detalles.count()}", "icon": "hand_meal"},
            ]
        )
        return additional_info

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.update(
            {
                "view": self,
                "object": self.object,
                "id_register": self.object.pk,
                "name_register": self.__get_client_full_name(self.object),
                "aditional_information": self.get_aditional_information(self.object),
            }
        )
        context_object_name = self.get_context_object_name(self.object)
        if context_object_name:
            kwargs[context_object_name] = self.object
        return kwargs

    def post(self, request, *args, **kwargs):
        cita = self.get_object()
        client_full_name = self.__get_client_full_name(cita)
        date_formatted = self.__get_date_time_formatted(cita)
        cita.delete()
        message = (
            "La cita de %(client_full_name)s para el día %(date)s fue eliminada exitosamente."
        ) % {
            "client_full_name": client_full_name,
            "date": date_formatted,
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


# endregion
"""========================================================================="""
