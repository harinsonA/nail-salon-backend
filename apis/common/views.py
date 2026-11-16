from rest_framework.views import APIView

from apis.common.guards import GuardChain


class ApiView(APIView):
    guard_chain = GuardChain()
    requires_session = True
    allows_temporary_password = False

    def perform_authentication(self, request):
        pass

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.guard_chain.run(request, self)
