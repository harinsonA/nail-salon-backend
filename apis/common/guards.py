from django.core.exceptions import ValidationError

from apis.common import errors
from apps.profiles.middleware import debe_cambiar_clave
from apps.profiles.permisos import SOLO_ADMINISTRACION, SOLO_CON_EQUIPO, administra_el_negocio
from apps.settings.preferences.registry import APP_MAINTENANCE, APP_MAINTENANCE_MESSAGE, APP_MODULE
from apps.settings.preferences.service import get_preference, get_preferences
from apps.settings.preferences.versions import AppVersion
from apps.tenancy.business_status import BusinessStatus
from apps.tenancy.business_status.messages import PAYMENT_PENDING
from apps.tenancy.models import Negocio
from apps.tenancy.user_limit import UserLimit
from apps.tenancy.user_limit.messages import OVER_LIMIT_LOGIN, TEAM_DISABLED

APP_VERSION_HEADER = "X-App-Version"

BUSINESS_UNAVAILABLE_CODES = {
    Negocio.Estado.PREPARANDO: "business_preparing",
    Negocio.Estado.PAUSADO: "business_paused",
    Negocio.Estado.CANCELADO: "business_cancelled",
}


class Guard:
    needs_user = False

    def check(self, request, view):
        raise NotImplementedError


class AppVersionGuard(Guard):
    def check(self, request, view):
        minimum = AppVersion.current()["minimum"]
        if not minimum:
            return
        version = request.headers.get(APP_VERSION_HEADER, "")
        try:
            version = AppVersion.clean(version)
        except ValidationError:
            version = ""
        if not version or AppVersion.is_above(minimum, version):
            raise errors.OutdatedVersion()


class AppEnabledGuard(Guard):
    def check(self, request, view):
        if not get_preference(APP_MODULE.key):
            raise errors.AppDisabled()


class MaintenanceGuard(Guard):
    def check(self, request, view):
        values = get_preferences([APP_MAINTENANCE.key, APP_MAINTENANCE_MESSAGE.key])
        if values[APP_MAINTENANCE.key]:
            raise errors.Maintenance(values[APP_MAINTENANCE_MESSAGE.key] or None)


class BusinessAvailableGuard(Guard):
    def check(self, request, view):
        status = BusinessStatus.for_request(request)
        unavailable = status.unavailable if status else None
        if unavailable:
            code = BUSINESS_UNAVAILABLE_CODES[status.negocio.estado]
            raise errors.BusinessUnavailable(unavailable.status_code, unavailable.message, code)


class SessionGuard(Guard):
    def check(self, request, view):
        if view.requires_session and not request.user.is_authenticated:
            raise errors.SessionRequired()


class UserLimitGuard(Guard):
    needs_user = True

    def check(self, request, view):
        if not UserLimit.for_request(request).lets_in(request.user):
            raise errors.UserLimitReached(OVER_LIMIT_LOGIN)


class TemporaryPasswordGuard(Guard):
    needs_user = True

    def check(self, request, view):
        if not view.allows_temporary_password and debe_cambiar_clave(request.user):
            raise errors.TemporaryPassword()


class PaymentPendingGuard(Guard):
    needs_user = True

    def check(self, request, view):
        status = BusinessStatus.for_request(request)
        if status and status.pauses_section(request.resolver_match.url_name, request.user):
            raise errors.PaymentPending(PAYMENT_PENDING)


class RolePermissionGuard(Guard):
    needs_user = True

    def check(self, request, view):
        url_name = request.resolver_match.url_name
        if url_name in SOLO_ADMINISTRACION and not administra_el_negocio(request.user):
            raise errors.Forbidden()
        if url_name in SOLO_CON_EQUIPO and not UserLimit.for_request(request).team_enabled:
            raise errors.TeamDisabled(TEAM_DISABLED)


class GuardChain:
    DEFAULT = (
        AppVersionGuard,
        AppEnabledGuard,
        MaintenanceGuard,
        BusinessAvailableGuard,
        SessionGuard,
        UserLimitGuard,
        TemporaryPasswordGuard,
        PaymentPendingGuard,
        RolePermissionGuard,
    )

    def __init__(self, guards=DEFAULT):
        self.guards = [guard() for guard in guards]

    def run(self, request, view):
        for guard in self.guards:
            if guard.needs_user and not request.user.is_authenticated:
                continue
            guard.check(request, view)
