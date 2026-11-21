from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.appointments.saving import AppointmentSaving
from apis.v1.appointments.serializers import (
    AppointmentCreateSerializer,
    AppointmentSavedSerializer,
)
from apps.appointments.editing import AppointmentSavedMessage
from apps.appointments.engine import AppointmentWriter
from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Views


class AppointmentsView(ApiView):
    http_method_names = ["post"]

    @staticmethod
    def saved(appointment, status_code):
        appointment = AppointmentSaving.reloaded(appointment)
        body = {"message": AppointmentSavedMessage.created(appointment), "appointment": appointment}
        return Response(AppointmentSavedSerializer(body).data, status=status_code)

    def create(self, request):
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        codigo_app = changes.get("codigo_app")
        existing = Cita.all_objects.filter(codigo_app=codigo_app).first() if codigo_app else None
        if existing:
            return self.saved(existing, status.HTTP_200_OK)
        data = AppointmentSaving(request).validated(changes)
        appointment = AppointmentWriter(request.user).create({**data, "codigo_app": codigo_app})
        return self.saved(appointment, status.HTTP_201_CREATED)

    @extend_schema(
        summary="Crear cita",
        description=(
            "Mismo formulario y reglas de la web. Lleva el resumen que mostró la app: el "
            "servidor lo vuelve a calcular y, si no coincide, no guarda (summary_mismatch). "
            "Cada servicio nuevo usa el menor entre el precio que vio la app y el actual; si "
            "bajó, responde prices_lowered. Con codigo_app repetido devuelve la cita ya creada."
        ),
        request=AppointmentCreateSerializer,
        responses={201: AppointmentSavedSerializer, 200: AppointmentSavedSerializer},
    )
    def post(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.create(request))


# endregion
"""========================================================================="""
