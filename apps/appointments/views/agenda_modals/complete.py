from datetime import datetime

from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView
from django import forms
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.panel import AppointmentPanel, person_name
from apps.appointments.views.agenda_modals.common import AgendaBaseModalView
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.currency import format_money
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import get_errors_to_response
from apps.payments.choices import EstadoPago, MetodoPago
from apps.payments.models import DetallePago, Pago

"""========================================================================="""
# region ........ Constants


AMOUNT_REQUIRED = "El monto abonado es requerido."
AMOUNT_TOO_HIGH = 'Si paga {total} o más, activa "Paga el total ahora".'


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AgendaConfirmationForm(BSModalModelForm):
    full_payment = forms.BooleanField(
        label="Paga el total ahora",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
    )
    down_payment = forms.IntegerField(
        label="Monto abonado",
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "0",
                "step": "500",
                "inputmode": "numeric",
            }
        ),
    )
    payment_method = forms.ChoiceField(
        label="Método",
        choices=MetodoPago.CHOICES,
        initial=MetodoPago.EFECTIVO,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    payment_reference = forms.CharField(
        label="Referencia",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "N° de comprobante o transferencia",
            }
        ),
    )
    observations = NoteField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "placeholder": "Ej.: pagará el resto la próxima semana",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remaining_payment_value = self.__get_initial_remaining_payment()

    def __get_initial_remaining_payment(self) -> int:
        total_amount = 0
        details = self.instance.detalles.values_list("precio_acordado")
        for detail in details:
            price_acorded = detail[0]
            total_amount += price_acorded
        return total_amount

    class Meta:
        model = Cita
        fields = []

    def save(self, commit=False):
        return self.instance

    def clean_down_payment(self):
        down_payment = self.cleaned_data.get("down_payment")
        if self.cleaned_data.get("full_payment"):
            return down_payment
        if down_payment is None:
            raise forms.ValidationError(AMOUNT_REQUIRED)
        if down_payment >= self.remaining_payment_value:
            total = format_money(self.remaining_payment_value)
            raise forms.ValidationError(AMOUNT_TOO_HIGH.format(total=total))
        return down_payment


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AgendaConfirmationModal(
    AppointmentAccessMixin, AgendaBaseModalView, BSModalUpdateView
):
    template_name = "appointments/agenda_confirmation_modal.html"
    model = Cita
    form_class = AgendaConfirmationForm

    def get_queryset(self):
        return super().get_queryset().filter(estado=Cita.EstadoChoices.PENDIENTE)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        services, subtotal, discounts = AppointmentPanel(
            self.object, self.request.user
        ).services()
        total = context["form"].remaining_payment_value
        context.update(
            {
                "modal_url": self.request.path,
                "services": services,
                "subtotal": format_money(subtotal),
                "discounts": format_money(-discounts) if discounts else format_money(0),
                "total": format_money(total),
                "total_value": int(total),
                "attended_by": person_name(self.request.user, self.request.user),
            }
        )
        return context

    def __get_message_success(self) -> str:
        return (
            "La cita de %(client_name)s para el día %(date)s a las %(time)s fue "
            "completada."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }

    @staticmethod
    def __get_payment_instance(
        object_base: Cita,
        client_full_name: str,
        full_payment: bool,
        details: dict,
        user,
    ) -> Pago:
        total_amount = details.get("detail_totals", 0)
        discount_amount = details.get("discount_totals", 0)
        appointment_date_time = timezone.make_aware(
            datetime.combine(object_base.fecha_agenda, object_base.hora_agenda)
        )
        payment_instance = Pago(
            cita=object_base,
            monto_total_cita=total_amount,
            cliente_nombre=client_full_name,
            fecha_cita=appointment_date_time,
            descuento_total=discount_amount,
            atendido_por=user,
            atendido_por_nombre=user_display_name(user),
        )
        if full_payment:
            payment_instance.estado_pago = EstadoPago.COMPLETADO
            payment_instance.fecha_pago_completado = timezone.now()
        payment_instance.save()
        return payment_instance

    @staticmethod
    def __save_payment_details(
        payment_instance: Pago,
        cleaned_data: dict,
        full_payment: bool,
        user,
    ) -> None:
        down_payment = cleaned_data.get("down_payment", 0)
        if not full_payment and not down_payment:
            return
        amount_paid = (
            payment_instance.monto_total_cita
            if full_payment
            else cleaned_data.get("down_payment", 0)
        )
        payment_method = cleaned_data.get("payment_method", MetodoPago.EFECTIVO)
        observation = cleaned_data.get("observations", "")
        payment_detail_instance = DetallePago(
            pago=payment_instance,
            fecha_pago=timezone.now(),
            monto_pago=amount_paid,
            metodo_pago=payment_method,
            notas_detalle=observation,
            registrado_por=user,
        )
        if payment_method != MetodoPago.EFECTIVO:
            payment_reference = cleaned_data.get("payment_reference") or None
            payment_detail_instance.referencia_pago = payment_reference
        payment_detail_instance.save()

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        details = self._get_details(self.object)
        client_full_name = self._get_client_full_name(self.object)
        full_payment = cleaned_data.get("full_payment", False)
        payment_instance = self.__get_payment_instance(
            object_base=self.object,
            client_full_name=client_full_name,
            full_payment=full_payment,
            details=details,
            user=self.request.user,
        )
        self.__save_payment_details(
            payment_instance=payment_instance,
            cleaned_data=cleaned_data,
            full_payment=full_payment,
            user=self.request.user,
        )
        self.object.estado = Cita.EstadoChoices.COMPLETADA
        self.object.save()
        message = self.__get_message_success()
        return JsonResponse({"message": message}, status=200)

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
