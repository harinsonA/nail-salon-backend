from django.contrib.auth.models import Group, Permission
from django.db.models import Q

"""========================================================================="""
# region ........ Constants


PANEL_PERMISSION_MODELS = [
    ("tenancy", "negocio", "Negocios"),
    ("tenancy", "persona", "Personas"),
    ("tenancy", "rubro", "Rubros"),
    ("auth", "user", "Usuarios"),
    ("auth", "group", "Grupos"),
]
PERMISSION_ACTIONS = [("view", "Ver"), ("add", "Agregar"), ("change", "Editar"), ("delete", "Eliminar")]


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def panel_permissions():
    condition = Q()
    for app_label, model, _ in PANEL_PERMISSION_MODELS:
        codenames = [f"{action}_{model}" for action, _ in PERMISSION_ACTIONS]
        condition |= Q(content_type__app_label=app_label, content_type__model=model, codename__in=codenames)
    return Permission.objects.filter(condition).select_related("content_type")


def panel_permission_ids():
    return set(panel_permissions().values_list("pk", flat=True))


def permission_action_labels():
    return [label for _, label in PERMISSION_ACTIONS]


def group_permission_map():
    panel_ids = panel_permission_ids()
    mapping = {}
    for group_id, permission_id in Group.permissions.through.objects.values_list("group_id", "permission_id"):
        if permission_id in panel_ids:
            mapping.setdefault(str(group_id), []).append(permission_id)
    return mapping


def build_permission_rows(direct_ids, inherited_ids=frozenset()):
    permissions = {
        (permission.content_type.app_label, permission.codename): permission for permission in panel_permissions()
    }
    rows = []
    for app_label, model, label in PANEL_PERMISSION_MODELS:
        cells = []
        for action, action_label in PERMISSION_ACTIONS:
            permission = permissions.get((app_label, f"{action}_{model}"))
            if permission is None:
                continue
            cells.append(
                {
                    "id": permission.pk,
                    "action": action_label,
                    "direct": permission.pk in direct_ids,
                    "inherited": permission.pk in inherited_ids,
                }
            )
        rows.append({"label": label, "cells": cells})
    return rows


def merge_panel_permissions(current_ids, selected_ids, kept_ids=frozenset()):
    outside_panel = set(current_ids) - panel_permission_ids()
    return outside_panel | (set(current_ids) & set(kept_ids)) | set(selected_ids)


# endregion
"""========================================================================="""
