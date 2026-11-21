import logging

from django.db.models import Prefetch
from rest_framework import serializers

from apis.common import errors, messages
from apis.v1.appointments.form_data import AppointmentFormData
from apps.appointments.editing import AppointmentForm
from apps.appointments.engine import AppointmentServices, AppointmentSummary
from apps.appointments.models import Cita, DetalleCita
from apps.payments.models import Pago

logger = logging.getLogger(__name__)


class AppointmentSaving:
    def __init__(self, request, appointment=None):
        self.request = request
        self.appointment = appointment

    def form(self, changes):
        return AppointmentForm(
            data=AppointmentFormData.for_form(changes),
            request=self.request,
            instance=self.appointment,
        )

    @staticmethod
    def lowered_service(line):
        service = line["service"]
        return {
            "servicio_id": service.pk,
            "nombre_servicio": service.nombre,
            "precio_servicio": int(line["price"]),
        }

    @classmethod
    def check_prices(cls, lines):
        lowered = AppointmentServices.lowered(lines)
        if not lowered:
            return
        names = ", ".join(f"«{line['service'].nombre}»" for line in lowered)
        raise errors.PricesLowered(
            messages.PRICES_LOWERED.format(names=names),
            extra={"services": [cls.lowered_service(line) for line in lowered]},
        )

    @staticmethod
    def check_summary(form, sent):
        summary = AppointmentSummary(form.draft, form.cleaned_data)
        differences = summary.differences(sent)
        if differences:
            logger.warning("Resumen de cita distinto al de la app: %s", ", ".join(differences))
            raise errors.SummaryMismatch(
                extra={"differences": differences, "summary": summary.as_dict()}
            )

    def validated(self, changes):
        form = self.form(changes)
        if not form.is_valid():
            raise serializers.ValidationError(AppointmentFormData.errors(form))
        self.check_prices(form.cleaned_data["services"])
        self.check_summary(form, changes["summary"])
        return form.cleaned_data

    @staticmethod
    def reloaded(appointment):
        return Cita.objects.prefetch_related(
            Prefetch("detalles", queryset=DetalleCita.objects.order_by("pk")),
            Prefetch("pago", queryset=Pago.objects.prefetch_related("detalles_pago")),
        ).get(pk=appointment.pk)
