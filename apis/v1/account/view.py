from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from apis.common.views import ApiView
from apis.v1.account.serializers import MessageSerializer, PasswordSerializer
from apps.profiles.middleware import debe_cambiar_clave
from apps.profiles.password import PasswordChange

"""========================================================================="""
# region ........ Views


class PasswordView(ApiView):
    allows_temporary_password = True
    http_method_names = ["post"]

    @extend_schema(
        summary="Cambiar clave",
        description=(
            "Con clave temporal pide new_password y confirm_password; si no, también current_password. "
            "Cierra la sesión web y este teléfono sigue dentro."
        ),
        request=PasswordSerializer,
        responses=MessageSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        field_errors = PasswordChange(user).change(
            data["current_password"],
            data["new_password"],
            data["confirm_password"],
            temporary=debe_cambiar_clave(user),
        )
        if field_errors:
            raise serializers.ValidationError(field_errors)
        request.auth.password_changed()
        return Response(MessageSerializer({"message": PasswordChange.SAVED_MESSAGE}).data)


# endregion
"""========================================================================="""
