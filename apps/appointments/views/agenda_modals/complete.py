from bootstrap_modal_forms.generic import BSModalUpdateView
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.completing import AppointmentCompletedMessage, CompletionForm
from apps.appointments.models import Cita
from apps.appointments.panel import AppointmentPanel, person_name
from apps.appointments.views.agenda_modals.common import AgendaBaseModalView
from apps.common.utils.currency import Money
from apps.common.utils.utils import get_errors_to_response

"""========================================================================="""
# region ........ Views


class AgendaConfirmationModal(
    AppointmentAccessMixin, AgendaBaseModalView, BSModalUpdateView
):
    template_name = "appointments/agenda_confirmation_modal.html"
    model = Cita
    form_class = CompletionForm

    def get_queryset(self):
        return super().get_queryset().filter(estado=Cita.EstadoChoices.PENDIENTE)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        completion = form.completion
        services, subtotal, discounts, _ = AppointmentPanel(
            self.object, self.request.user
        ).services()
        total = completion.remaining
        advance = completion.advance_part()
        context.update(
            {
                "modal_url": self.request.path,
                "services": services,
                "subtotal": Money.format(subtotal),
                "discounts": Money.format(-discounts) if discounts else Money.format(0),
                "services_total": Money.format(completion.services_total),
                "prepaid": Money.format(-completion.prepaid) if completion.prepaid else "",
                "advance": Money.format(-advance) if advance else "",
                "reservation": completion.reservation_card(),
                "settled_hint": completion.settled_hint(),
                "total": Money.format(total),
                "total_value": int(total),
                "complete_config": {
                    "total": int(total),
                    "prepaid": int(completion.prepaid),
                    "servicesTotal": int(completion.services_total),
                    "fullLabel": form.fields["full_payment"].label,
                },
                "attended_by": person_name(self.request.user, self.request.user),
            }
        )
        return context

    def form_valid(self, form):
        form.complete(self.request.user)
        message = AppointmentCompletedMessage.text(self.object)
        return JsonResponse({"message": message}, status=200)

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
