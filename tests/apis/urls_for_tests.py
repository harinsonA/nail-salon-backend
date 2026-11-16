from django.urls import include, path
from rest_framework.response import Response

from apis.common.views import ApiView


class SampleView(ApiView):
    def get(self, request, *args, **kwargs):
        return Response({"ok": True})


class TemporaryPasswordSampleView(SampleView):
    allows_temporary_password = True


class OpenSampleView(SampleView):
    requires_session = False


urlpatterns = [
    path("", include("nail_salon_api.urls")),
    path("api/v1/sample/", SampleView.as_view(), name="api_sample"),
    path("api/v1/sample/admin/", SampleView.as_view(), name="api_sample_admin"),
    path("api/v1/sample/team/", SampleView.as_view(), name="api_sample_team"),
    path("api/v1/sample/password/", TemporaryPasswordSampleView.as_view(), name="api_sample_password"),
    path("api/v1/sample/open/", OpenSampleView.as_view(), name="api_sample_open"),
]
