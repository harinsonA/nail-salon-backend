from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse

UNAUTHORIZED_RESPONSE_AUTO = "auto"
UNAUTHORIZED_RESPONSE_JSON = "json"
UNAUTHORIZED_RESPONSE_REDIRECT = "redirect"

SESSION_EXPIRED_MESSAGE = "Tu sesión expiró, vuelve a iniciar sesión."


class ProtectedView(LoginRequiredMixin):
    unauthorized_response_kind = UNAUTHORIZED_RESPONSE_AUTO
    session_expired_message = SESSION_EXPIRED_MESSAGE

    def wants_json_response(self) -> bool:
        headers = self.request.headers
        if headers.get("x-requested-with") == "XMLHttpRequest":
            return True
        return headers.get("accept", "").startswith("application/json")

    def get_unauthorized_response_kind(self) -> str:
        if self.unauthorized_response_kind != UNAUTHORIZED_RESPONSE_AUTO:
            return self.unauthorized_response_kind
        if self.wants_json_response():
            return UNAUTHORIZED_RESPONSE_JSON
        return UNAUTHORIZED_RESPONSE_REDIRECT

    def unauthorized_json_response(self) -> JsonResponse:
        return JsonResponse(
            {
                "message": self.session_expired_message,
                "redirect": reverse("login"),
            },
            status=401,
        )

    def handle_no_permission(self):
        if self.get_unauthorized_response_kind() == UNAUTHORIZED_RESPONSE_JSON:
            return self.unauthorized_json_response()
        return super().handle_no_permission()


class ProtectedAjaxView(ProtectedView):
    unauthorized_response_kind = UNAUTHORIZED_RESPONSE_JSON


class ProtectedExportView(ProtectedView):
    unauthorized_response_kind = UNAUTHORIZED_RESPONSE_REDIRECT
