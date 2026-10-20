from django.shortcuts import redirect


class DjangoPagesRedirectMixin:
    def changelist_redirect(self):
        opts = self.model._meta
        return redirect(f"admin:{opts.app_label}_{opts.model_name}_changelist")

    def add_view(self, request, form_url="", extra_context=None):
        return self.changelist_redirect()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return self.changelist_redirect()

    def delete_view(self, request, object_id, extra_context=None):
        return self.changelist_redirect()

    def history_view(self, request, object_id, extra_context=None):
        return self.changelist_redirect()

    def history_form_view(self, request, object_id, version_id, extra_context=None):
        return self.changelist_redirect()
