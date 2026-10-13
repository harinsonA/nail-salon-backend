from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.urls import reverse

from apps.common.base_list_view_ajax import AjaxListViewBase
from apps.common.views.base_views import SESSION_EXPIRED_MESSAGE

FORBIDDEN_MESSAGE = "No tienes permiso para ver esta información del panel."


class PanelAccessMixin:
    admin_site = None
    model_admin = None

    def dispatch(self, request, *args, **kwargs):
        if not self.admin_site.has_permission(request):
            return self.handle_no_session()
        if self.model_admin is not None and not self.model_admin.has_view_permission(request):
            return self.handle_forbidden()
        return super().dispatch(request, *args, **kwargs)

    def get_login_url(self):
        return reverse("admin:login", current_app=self.admin_site.name)


class PanelView(PanelAccessMixin):
    def handle_no_session(self):
        return redirect_to_login(self.request.get_full_path(), self.get_login_url())

    def handle_forbidden(self):
        raise PermissionDenied

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self.admin_site.each_context(self.request)}


class PanelAjaxView(PanelAccessMixin):
    def handle_no_session(self):
        return JsonResponse({"message": SESSION_EXPIRED_MESSAGE, "redirect": self.get_login_url()}, status=401)

    def handle_forbidden(self):
        return JsonResponse({"message": FORBIDDEN_MESSAGE}, status=403)


class PanelListViewAjax(PanelAjaxView, AjaxListViewBase):
    pass
