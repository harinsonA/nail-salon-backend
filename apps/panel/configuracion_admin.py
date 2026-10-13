from django.contrib.admin.apps import AdminConfig


class PanelAdminConfig(AdminConfig):
    default_site = "apps.panel.sitio.PanelAdminSite"
