import json

from datetime import date, datetime
from django import forms
from django.contrib import messages
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalReadView

from apps.appointments.models import DetalleCita, Cita
from apps.appointments.views.handler import HandlerAgendaList
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.payments.choices import MetodoPago, EstadoPago
from apps.payments.models import Pago, DetallePago
from apps.common.custom_time_fields import (
    CustomDateField,
    MONTH_NUMBER_TO_NAME,
)
from apps.common.utils.dates import format_full_date
from apps.common.utils.utils import get_errors_to_response
from apps.services.models import Servicio

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_CONTROL_TEXTAREA_CLASS = f"{FORM_CONTROL_CLASS} form-control--textarea"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class AgendaFilterForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        required=False,
        initial=Cita.EstadoChoices.PENDIENTE,
        choices=Cita.EstadoChoices.choices,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_selected = CustomDateField(
        required=False,
        label="Fecha de la cita",
    )

    def clean(self):
        cleaned_data = super().clean()
        agendaStatus = cleaned_data.get("status", Cita.EstadoChoices.PENDIENTE)
        date_selected = cleaned_data.get("date_selected")

        filters = {"estado": agendaStatus}

        if date_selected:
            filters["fecha_agenda__in"] = [date_selected]
        return filters


class AgendaModalForm(BSModalModelForm):
    service = forms.ModelChoiceField(
        queryset=Servicio.activos.all(),
        required=False,
        label="Servicio",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_agenda = CustomDateField(
        required=True,
        label="Fecha de la cita",
    )
    time_agenda = forms.TimeField(
        required=True,
        label="Hora de la cita",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )
    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )
    quantity = forms.IntegerField(
        label="Cantidad",
        initial=1,
        min_value=1,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "1",
                "placeholder": "1",
            }
        ),
    )
    discount_amount = forms.IntegerField(
        label="Descuento",
        initial=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "0",
                "placeholder": "1000",
            }
        ),
    )

    def clean_date_agenda(self):
        date_agenda = self.cleaned_data.get("date_agenda")
        if not date_agenda:
            raise forms.ValidationError("La fecha de la cita es obligatoria.")
        # CustomDateField.to_python() ya convirtió el string a objeto date
        return date_agenda

    class Meta:
        model = Cita
        fields = []

    def save(self, commit=False):
        return self.instance


class AgendaConfirmationForm(BSModalModelForm):
    payment_method = forms.ChoiceField(
        label="Método de pago",
        choices=MetodoPago.CHOICES,
        required=False,
        initial=MetodoPago.EFECTIVO,
        widget=forms.Select(
            attrs={
                "class": FORM_SELECT_CLASS,
            }
        ),
    )
    payment_reference = forms.CharField(
        label="Referencia de pago",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Nro. de recibo, transacción, etc.",
            }
        ),
    )
    full_payment = forms.BooleanField(
        label="Pago completo",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )
    remaining_payment = forms.IntegerField(
        label="Restante",
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "0",
                "placeholder": "0",
                "readonly": "readonly",
            }
        ),
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
                "placeholder": "0",
            }
        ),
    )

    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remaining_payment_value = self.__get_initial_remaining_payment()
        self.fields["remaining_payment"].initial = self.remaining_payment_value

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
        down_payment = self.cleaned_data.get("down_payment", 0)
        if down_payment >= self.remaining_payment_value:
            raise forms.ValidationError(
                "El monto abonado no puede ser mayor o igual al total de la cita."
            )
        return down_payment

    def clean_payment_reference(self):
        payment_reference = self.cleaned_data.get("payment_reference", "")
        payment_method = self.cleaned_data.get("payment_method", "")

        is_cash = payment_method == MetodoPago.EFECTIVO
        has_no_reference = not payment_reference or not payment_reference.strip()

        if not is_cash and has_no_reference:
            raise forms.ValidationError("Debe ingresar una referencia de pago.")

        return payment_reference.strip()


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class AppointmentsView(TemplateView):
    template_name = "appointments/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = date.today()
        return f"{today.strftime('%B %Y')}".capitalize()

    @staticmethod
    def get_date_instance(**kwargs) -> date:
        _date = kwargs.get("date", "")
        date_instance = (
            datetime.strptime(_date, "%Y-%m-%d").date() if _date else date.today()
        )
        return date_instance

    def get_date_initial(self, **kwargs):
        _date = kwargs.get("date", "")
        if _date:
            date_instance = datetime.strptime(_date, "%Y-%m-%d").date()
            return date_instance.strftime("%d/%m/%Y")
        return ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _date_selected = context["date"]
        date_instance = self.get_date_instance(date=_date_selected)
        date_initial = self.get_date_initial(date=_date_selected)
        context.update(
            {
                "filter_form": AgendaFilterForm(
                    initial={"date_selected": date_initial}
                ),
                "url_agenda_list": reverse_lazy("agenda_list"),
                "url_agenda_create": reverse_lazy(
                    "create_appointment_from_calendar", args=[_date_selected]
                ),
                "full_date": format_full_date(date_instance),
                "date_initial": date_initial,
            }
        )
        return context


class AgendaListView(BaseListViewAjax):
    model = Cita
    filter_form_class = AgendaFilterForm

    field_list = [
        "pk",
        "cliente_full_name",
        "hora_agenda",
        "estado",
        "cantidad_servicios",
    ]

    ordering_fields = {
        "0": "hora_agenda",
        "1": "cliente_full_name",
        "2": "estado",
        "3": "cantidad_servicios",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cliente")
            .prefetch_related("detalles")
            .annotate(
                cantidad_servicios=Count("detalles"),
                cliente_full_name=Concat(
                    "cliente__nombre", Value(" "), "cliente__apellido"
                ),
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["formatted_time"] = HandlerAgendaList.get_formatted_time(**value)
            value["agenda_see_modal_url"] = reverse_lazy(
                "agenda_see_modal", args=[value["pk"]]
            )
            value.update(HandlerAgendaList.get_options(value["pk"], value["estado"]))
        return values

    def additional_data(self, queryset):
        _filters = self.get_filters()
        date_selected = _filters.get("fecha_agenda__in", None)
        if not date_selected:
            return {}
        additional_data = self.model.objects.filter(
            fecha_agenda__in=date_selected
        ).aggregate(
            total_pendientes=Count("pk", filter=Q(estado=Cita.EstadoChoices.PENDIENTE)),
            total_completadas=Count(
                "pk", filter=Q(estado=Cita.EstadoChoices.COMPLETADA)
            ),
            total_canceladas=Count("pk", filter=Q(estado=Cita.EstadoChoices.CANCELADA)),
        )
        return {**additional_data}


class AgendaUpdateModalView(BSModalUpdateView):
    template_name = "appointments/agenda_detail_modal.html"
    model = Cita
    form_class = AgendaModalForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "date_agenda": self.object.fecha_agenda.strftime("%d/%m/%Y"),
                "time_agenda": self.object.hora_agenda.strftime("%H:%M"),
            }
        )
        return initial

    def get_success_url(self):
        return reverse_lazy("agenda_list")

    @staticmethod
    def __get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_date_formatted(object_base) -> str:
        return object_base.fecha_agenda.strftime("%d/%m/%Y")

    @staticmethod
    def __get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def __get_duration_in_minutes(detail) -> int:
        if not detail.duracion_estimada_servicio:
            return 0
        return int(detail.duracion_estimada_servicio.total_seconds() / 60)

    def __get_service_data(self, object_base) -> list:
        agenda_details = list(object_base.detalles.all())
        if not agenda_details:
            return []
        return [
            {
                "detalle_id": detail.pk,
                "total": float(detail.precio_acordado),
                "cantidad": detail.cantidad_servicios,
                "descuento": float(detail.descuento),
                "id": detail.servicio_id,
                "nombre": detail.nombre_servicio,
                "precio": float(detail.precio_servicio),
                "duracion_estimada": self.__get_duration_in_minutes(detail),
            }
            for detail in agenda_details
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]
        self.__get_service_data(object_base)
        context.update(
            {
                "client_full_name": self.__get_client_full_name(object_base),
                "date_formatted": self.__get_date_formatted(object_base),
                "time_formatted": self.__get_time_formatted(object_base),
                "service_data": json.dumps(self.__get_service_data(object_base)),
            }
        )
        return context

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)

    @staticmethod
    def __get_json(data):
        try:
            return json.loads(data)
        except Exception:
            return None

    @staticmethod
    def __delete_detail_agenda(agenda_id, detail_ids):
        DetalleCita.objects.filter(cita_id=agenda_id, pk__in=detail_ids).delete()

    def save_detail_agenda(self, service_data):
        new_services = []
        for service in service_data:
            detail_id = service.get("detalle_id", None)
            is_service_ready = (
                not detail_id
                or not isinstance(detail_id, str)
                or not detail_id.startswith("000_")
            )

            if is_service_ready:
                continue
            servicio = Servicio.objects.filter(pk=service.get("id")).first()
            new_services.append(
                DetalleCita(
                    cita=self.object,
                    servicio=servicio,
                    nombre_servicio=servicio.nombre if servicio else "",
                    precio_servicio=servicio.precio if servicio else 0,
                    duracion_estimada_servicio=servicio.duracion_estimada
                    if servicio
                    else None,
                    cantidad_servicios=service.get("cantidad", 1),
                    precio_acordado=service.get("total", 0),
                    descuento=service.get("descuento", 0),
                    notas_detalle=service.get("observaciones", ""),
                )
            )
        if not new_services:
            return
        DetalleCita.objects.bulk_create(new_services)

    def form_valid(self, form):
        if self.object.estado != Cita.EstadoChoices.PENDIENTE:
            message = "Solo se pueden modificar las agendas en estado Pendiente."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        services_selected = self.__get_json(
            self.request.POST.get("servicesSelected", "")
        )
        if not services_selected:
            message = "No se seleccionaron servicios para la agenda."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )

        services_to_delete_selected = self.__get_json(
            self.request.POST.get("servicesToDeleteSelected", "")
        )
        if services_to_delete_selected:
            self.__delete_detail_agenda(
                agenda_id=self.object.pk,
                detail_ids=services_to_delete_selected,
            )
        cleaned_data = form.cleaned_data
        self.object.fecha_agenda = cleaned_data.get("date_agenda")
        self.object.hora_agenda = cleaned_data.get("time_agenda")
        self.object.save()
        self.save_detail_agenda(services_selected)
        message = (
            "Agenda de %(client_name)s fue actualizada para el día %(date)s a las %(time)s."
        ) % {
            "client_name": self.__get_client_full_name(self.object),
            "date": self.__get_date_formatted(self.object),
            "time": self.__get_time_formatted(self.object),
        }
        messages.success(self.request, message)
        return JsonResponse(
            {"detail": message},
            status=200,
        )


class AgendaSeeModalView(BSModalReadView):
    template_name = "appointments/agenda_see_modal.html"
    model = Cita

    @staticmethod
    def get_services_data(object_base):
        appointment_details = object_base.detalles.all().values_list(
            "pk",
            "nombre_servicio",
            "cantidad_servicios",
            "precio_servicio",
            "precio_acordado",
            "descuento",
        )
        services_data = []
        for detail in appointment_details:
            (
                detail_id,
                service_name,
                quantity_services,
                service_price,
                price_acorded,
                discount,
            ) = detail
            services_data.append(
                {
                    "detail_id": detail_id,
                    "name": service_name,
                    "quantity": quantity_services,
                    "price": service_price,
                    "total": service_price * quantity_services,
                    "discount": discount,
                    "price_acorded": price_acorded,
                }
            )
        return services_data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]
        context.update({"services": self.get_services_data(object_base)})
        return context


class AgendaBaseModalView:
    """Base class for agenda modal views that provides common context data"""

    @staticmethod
    def _get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def _get_date_formatted(object_base) -> str:
        day = object_base.fecha_agenda.day
        month = MONTH_NUMBER_TO_NAME[object_base.fecha_agenda.month]
        year = object_base.fecha_agenda.year
        return f"{day} de {month} del {year}"

    @staticmethod
    def _get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def _get_phone_number(object_base) -> str:
        return object_base.cliente.telefono or "Sin teléfono"

    @staticmethod
    def _get_details(object_base) -> int:
        counts = object_base.detalles.count()
        details = object_base.detalles.values_list(
            "precio_acordado",
            "descuento",
            "cantidad_servicios",
            "precio_servicio",
        )
        service_totals = 0
        detail_totals = 0
        discount_totals = 0
        for detail in details:
            total, discount, quantity, service_price = detail
            detail_totals += total
            discount_totals += discount
            service_totals += service_price * quantity
        return {
            "services_count": counts,
            "detail_totals": detail_totals,
            "discount_totals": discount_totals,
            "service_totals": service_totals,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]

        context.update(
            {
                "appointment_id": object_base.pk,
                "client_full_name": self._get_client_full_name(object_base),
                "date_formatted": self._get_date_formatted(object_base),
                "time_formatted": self._get_time_formatted(object_base),
                "phone_number": self._get_phone_number(object_base),
                **self._get_details(object_base),
            }
        )
        return context


class AgendaCancelModalView(AgendaBaseModalView, BSModalReadView):
    template_name = "appointments/agenda_cancel_modal.html"
    model = Cita

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.estado != Cita.EstadoChoices.PENDIENTE:
            message = "Solo se pueden cancelar las agendas en estado Pendiente."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        self.object.estado = Cita.EstadoChoices.CANCELADA
        self.object.save()
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue cancelada."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


class AgendaRestoreModalView(AgendaBaseModalView, BSModalReadView):
    template_name = "appointments/agenda_restore_modal.html"
    model = Cita

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.estado != Cita.EstadoChoices.CANCELADA:
            message = "Solo se pueden restaurar las agendas en estado Cancelada."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        self.object.estado = Cita.EstadoChoices.PENDIENTE
        self.object.save()
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue restaurada a Pendiente."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


class AgendaDeleteModalView(BSModalReadView):
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


class AgendaConfirmationModal(AgendaBaseModalView, BSModalUpdateView):
    template_name = "appointments/agenda_confirmation_modal.html"
    model = Cita
    form_class = AgendaConfirmationForm

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
        )
        if payment_method != MetodoPago.EFECTIVO:
            payment_reference = cleaned_data.get("payment_reference", "")
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
        )
        self.__save_payment_details(
            payment_instance=payment_instance,
            cleaned_data=cleaned_data,
            full_payment=full_payment,
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
