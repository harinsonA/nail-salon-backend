from django.views import defaults

"""========================================================================="""
# region ........ Views


def sin_permiso_en_el_panel(request, exception=None):
    return defaults.permission_denied(request, exception, template_name="admin/sin_permiso.html")


# endregion
"""========================================================================="""
