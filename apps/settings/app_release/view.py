import hmac
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.settings.preferences.registry import APP_LATEST_VERSION
from apps.settings.preferences.service import set_preference
from apps.settings.preferences.versions import AppVersion

"""========================================================================="""
# region ........ Constants


BEARER_PREFIX = "Bearer "
RELEASE_REASON = "Publicación automática"
UNAUTHORIZED_MESSAGE = "Clave de publicación inválida."
INVALID_BODY_MESSAGE = "El cuerpo debe ser JSON con el campo version."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def has_release_secret(request) -> bool:
    secret = settings.APP_RELEASE_SECRET
    header = request.headers.get("Authorization", "")
    if not secret or not header.startswith(BEARER_PREFIX):
        return False
    return hmac.compare_digest(header[len(BEARER_PREFIX):].encode(), secret.encode())


def read_version(request):
    try:
        body = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(body, dict) or not isinstance(body.get("version"), str):
        return None
    return body["version"]


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


@method_decorator(csrf_exempt, name="dispatch")
class AppReleaseView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        if not has_release_secret(request):
            return JsonResponse({"message": UNAUTHORIZED_MESSAGE}, status=401)
        version = read_version(request)
        if version is None:
            return JsonResponse({"message": INVALID_BODY_MESSAGE}, status=400)
        try:
            version = AppVersion.clean(version)
            if not version:
                raise ValidationError(INVALID_BODY_MESSAGE)
            current = AppVersion.current()
            AppVersion.check_range(current["minimum"], version)
        except ValidationError as error:
            return JsonResponse({"message": error.messages[0]}, status=400)
        changed = version != current["latest"]
        if changed:
            set_preference(APP_LATEST_VERSION.key, version, reason=RELEASE_REASON)
        return JsonResponse({"version": version, "changed": changed})


# endregion
"""========================================================================="""
