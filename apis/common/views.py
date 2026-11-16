from rest_framework.views import APIView

from apis.common import errors
from apis.common.authentication import BearerKeyAuthentication
from apis.common.guards import GuardChain


class ApiView(APIView):
    authentication_classes = [BearerKeyAuthentication]
    guard_chain = GuardChain()
    requires_session = True
    allows_temporary_password = False

    def perform_authentication(self, request):
        pass

    def throttled(self, request, wait):
        raise errors.TooManyRequests()

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.guard_chain.run(request, self)
