from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.base_list_view_ajax import AjaxListViewBase
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import SESSION_EXPIRED_MESSAGE

"""========================================================================="""
# region ........ Constants


FORBIDDEN_MESSAGE = "No tienes permiso para ver esta información del panel."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class PanelAccessMixin:
    admin_site = None
    model_admin = None

    def dispatch(self, request, *args, **kwargs):
        if not self.admin_site.has_permission(request):
            return self.handle_no_session()
        if self.model_admin is not None and not self.has_model_permission(request):
            return self.handle_forbidden()
        return super().dispatch(request, *args, **kwargs)

    def has_model_permission(self, request):
        return self.model_admin.has_view_permission(request)

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


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class PanelListViewAjax(PanelAjaxView, AjaxListViewBase):
    pass


class PanelCreateModalView(PanelAjaxView, BSModalFormView):
    success_message = "«%(name)s» creado exitosamente."

    def has_model_permission(self, request):
        return self.model_admin.has_add_permission(request)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def create_object(self, form):
        raise NotImplementedError

    def form_invalid(self, form):
        return JsonResponse({"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST)

    def form_valid(self, form):
        obj = self.create_object(form)
        self.model_admin.log_addition(self.request, obj, [{"added": {}}])
        return JsonResponse({"message": self.success_message % {"name": str(obj)}})


class PanelUpdateModalView(PanelAjaxView, BSModalFormView):
    success_message = "«%(name)s» actualizado exitosamente."

    def has_model_permission(self, request):
        return self.model_admin.has_change_permission(request, self.get_object())

    def get_object(self):
        if not hasattr(self, "_object"):
            obj = self.model_admin.get_object(self.request, str(self.kwargs["pk"]))
            if obj is None:
                raise Http404
            self._object = obj
        return self._object

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.get_object()}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path, "object": self.get_object()}

    def update_object(self, form):
        raise NotImplementedError

    def form_invalid(self, form):
        return JsonResponse({"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST)

    def form_valid(self, form):
        obj = self.update_object(form)
        changed = [str(form.fields[name].label) for name in form.changed_data]
        self.model_admin.log_change(self.request, obj, [{"changed": {"fields": changed}}] if changed else [])
        return JsonResponse({"message": self.success_message % {"name": str(obj)}})


class PanelDeleteModalView(PanelAjaxView, BSModalDeleteView):
    template_name = "common/delete_modal.html"
    success_message = "«%(name)s» eliminado exitosamente."
    blocked_message = (
        "No se puede eliminar «%(name)s»: tiene registros relacionados protegidos "
        "o que no tienes permiso para eliminar."
    )
    in_use_message = ""

    def has_model_permission(self, request):
        return self.model_admin.has_delete_permission(request, self.get_object())

    def get_object(self, queryset=None):
        obj = self.model_admin.get_object(self.request, str(self.kwargs["pk"]))
        if obj is None:
            raise Http404
        return obj

    def get_additional_information(self, obj):
        return []

    def is_blocked(self, obj):
        return False

    def get_blocked_reason(self, obj):
        return self.in_use_message % {"name": str(obj)} if self.is_blocked(obj) else ""

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        return {
            **kwargs,
            "view": self,
            "object": obj,
            "id_register": obj.pk,
            "name_register": str(obj),
            "aditional_information": self.get_additional_information(obj),
            "blocked_reason": self.get_blocked_reason(obj),
        }

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        name = str(obj)
        blocked_reason = self.get_blocked_reason(obj)
        if blocked_reason:
            return JsonResponse({"message": blocked_reason}, status=HTTP_400_BAD_REQUEST)
        _, _, perms_needed, protected = self.model_admin.get_deleted_objects([obj], request)
        if perms_needed or protected:
            return JsonResponse({"message": self.blocked_message % {"name": name}}, status=HTTP_400_BAD_REQUEST)
        self.model_admin.log_deletions(request, [obj])
        self.model_admin.delete_model(request, obj)
        return JsonResponse({"message": self.success_message % {"name": name}})


# endregion
"""========================================================================="""
