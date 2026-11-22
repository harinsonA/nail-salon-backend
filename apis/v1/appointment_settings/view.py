from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from apis.common.views import ApiView
from apis.v1.appointment_settings.serializers import ReservationSerializer
from apis.v1.me.preferences_data import PreferencesData
from apis.v1.me.serializers import PreferencesSavedSerializer
from apps.appointments.reservation_settings import ReservationSettings, ReservationSettingsForm

"""========================================================================="""
# region ........ Views


class ReservationView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar la reserva de las citas",
        description=(
            "Solo lo que cambió. Mismas reglas de la configuración de citas de la web: "
            "encendida exige el valor y apagada limpia los demás. Solo administración."
        ),
        request=ReservationSerializer,
        responses=PreferencesSavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        serializer = ReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = ReservationSettingsForm(data=ReservationSettings.form_data(serializer.validated_data))
        if not form.is_valid():
            raise serializers.ValidationError(ReservationSettings.errors(form))
        ReservationSettings.save(form)
        return Response(
            PreferencesSavedSerializer(
                {"message": ReservationSettings.SAVED_MESSAGE, "preferences": PreferencesData.of(request.user)}
            ).data
        )


# endregion
"""========================================================================="""
