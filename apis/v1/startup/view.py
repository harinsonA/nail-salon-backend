from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apis.common.guards import GuardChain
from apis.common.views import ApiView
from apis.v1.startup.serializers import StartupSerializer
from apps.common.utils.currency import Currency
from apps.settings.preferences.registry import (
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
    APP_MODULE,
)
from apps.settings.preferences.service import get_preferences
from apps.tenancy.business_status import BusinessStatus

"""========================================================================="""
# region ........ Constants


STARTUP_PREFERENCES = [
    APP_MODULE.key,
    APP_MAINTENANCE.key,
    APP_MAINTENANCE_MESSAGE.key,
    APP_MINIMUM_VERSION.key,
    APP_LATEST_VERSION.key,
]


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class StartupView(ApiView):
    guard_chain = GuardChain(guards=())
    requires_session = False
    http_method_names = ["get"]

    @extend_schema(
        summary="Startup",
        description="Valida el negocio al abrir la app. No pide sesión ni pasa por la cadena de guardias.",
        responses=StartupSerializer,
    )
    def get(self, request, *args, **kwargs):
        return Response(StartupSerializer(self.startup_data(request.tenant)).data)

    @staticmethod
    def startup_data(negocio):
        values = get_preferences(STARTUP_PREFERENCES)
        return {
            "business": {
                "nombre": negocio.nombre,
                "estado": negocio.estado,
                "overdue": BusinessStatus(negocio).is_overdue,
            },
            "app_enabled": values[APP_MODULE.key],
            "maintenance": {
                "active": values[APP_MAINTENANCE.key],
                "message": values[APP_MAINTENANCE_MESSAGE.key] or None,
            },
            "version": {
                "minimum": values[APP_MINIMUM_VERSION.key] or None,
                "latest": values[APP_LATEST_VERSION.key] or None,
            },
            "currency": Currency.of(negocio),
            "zona_horaria": negocio.zona_horaria,
        }


# endregion
"""========================================================================="""
