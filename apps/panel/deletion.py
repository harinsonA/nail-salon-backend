import threading
from contextlib import contextmanager

from django.conf import settings
from django.db import connection
from django.db.models import deletion
from django_tenants.routers import TenantSyncRouter
from django_tenants.utils import get_public_schema_name

_state = threading.local()
_router = TenantSyncRouter()
_original_candidate_relations = getattr(
    deletion.get_candidate_relations_to_delete, "__wrapped__", deletion.get_candidate_relations_to_delete
)


def apps_in_current_schema():
    if connection.schema_name == get_public_schema_name():
        return settings.SHARED_APPS
    return settings.TENANT_APPS


def candidate_relations_to_delete(opts):
    relations = _original_candidate_relations(opts)
    if not getattr(_state, "active", False):
        return relations
    apps_list = apps_in_current_schema()
    return (
        relation
        for relation in relations
        if _router.app_in_list(relation.related_model._meta.app_label, apps_list)
    )


candidate_relations_to_delete.__wrapped__ = _original_candidate_relations
deletion.get_candidate_relations_to_delete = candidate_relations_to_delete


@contextmanager
def deletion_limited_to_current_schema():
    previous = getattr(_state, "active", False)
    _state.active = True
    try:
        yield
    finally:
        _state.active = previous


class CurrentSchemaDeletionMixin:
    def get_deleted_objects(self, objs, request):
        with deletion_limited_to_current_schema():
            return super().get_deleted_objects(objs, request)

    def delete_model(self, request, obj):
        with deletion_limited_to_current_schema():
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with deletion_limited_to_current_schema():
            super().delete_queryset(request, queryset)
