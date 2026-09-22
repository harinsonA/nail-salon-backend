from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView


class SessionPingView(ProtectedAjaxView, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        return JsonResponse({"message": "Sesión activa"})
