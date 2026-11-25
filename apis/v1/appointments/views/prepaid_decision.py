import json

from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.appointments.lookup import AppointmentLookup
from apis.v1.appointments.saving import AppointmentSaving
from apis.v1.appointments.serializers import AppointmentSavedSerializer
from apps.appointments.engine import AppointmentLockedError, AppointmentRuleError

"""========================================================================="""
# region ........ Views


class PrepaidDecisionView(ApiView):
    http_method_names = ["get", "post"]
    status = None
    wrong_status_message = None
    engine_class = None
    card_class = None
    card_serializer = None
    request_serializer = None
    form_class = None
    field = None
    message_class = None

    def appointment(self, request, pk, lock=False):
        appointment = AppointmentLookup.visible(request.user, pk, lock)
        if appointment.estado != self.status:
            raise errors.Conflict(self.wrong_status_message)
        return appointment

    def open(self, request, pk):
        appointment = self.appointment(request, pk)
        card = self.card_class(appointment, request.user).build()
        return Response(self.card_serializer(card).data)

    def run(self, engine, decision):
        raise NotImplementedError

    @transaction.atomic
    def confirm(self, request, pk):
        serializer = self.request_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        appointment = self.appointment(request, pk, lock=True)
        engine = self.engine_class(appointment, request.user)
        try:
            engine.check()
        except AppointmentLockedError as error:
            raise errors.Forbidden(error.message) from error
        except AppointmentRuleError as error:
            raise errors.Conflict(error.message) from error
        if engine.rows_changed(changes["seen"]):
            raise errors.Conflict(messages.APPOINTMENT_PREPAID_CHANGED)
        form = self.form_class(
            data={self.field: json.dumps(request.data.get(self.field))}, engine=engine
        )
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        self.run(engine, form.cleaned_data[self.field])
        appointment = AppointmentSaving.reloaded(appointment)
        body = {"message": self.message_class.text(appointment), "appointment": appointment}
        return Response(AppointmentSavedSerializer(body).data)

    def post(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.confirm(request, kwargs["pk"]))


# endregion
"""========================================================================="""
