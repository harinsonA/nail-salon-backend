from django.views.generic import TemplateView

"""========================================================================="""
# region ........ Views


class InicioPanelView(TemplateView):
    template_name = "panel/inicio.html"
    admin_site = None

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **self.admin_site.each_context(self.request)}


# endregion
"""========================================================================="""
