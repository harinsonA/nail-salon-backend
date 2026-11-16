from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apis.common.guards import GuardChain
from apis.common.messages import NOT_FOUND
from apis.common.views import ApiView
from apps.common.api_request import ApiRequest

"""========================================================================="""
# region ........ Mixins


class LocalOnlyMixin:
    guard_chain = GuardChain(guards=())
    requires_session = False
    schema = None

    def dispatch(self, request, *args, **kwargs):
        if not settings.DEBUG:
            return ApiRequest.error_response(404, NOT_FOUND)
        return super().dispatch(request, *args, **kwargs)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class SchemaView(LocalOnlyMixin, ApiView, SpectacularAPIView):
    pass


class DocsView(LocalOnlyMixin, ApiView, SpectacularSwaggerView):
    url_name = "api_schema"


# endregion
"""========================================================================="""
