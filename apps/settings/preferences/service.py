from django.db.models import Q

from apps.settings.preferences.constants import Scope
from apps.settings.preferences.models import Preference
from apps.settings.preferences.registry import PREFERENCES


def resolve_scope_id(definition, user) -> str:
    if definition.scope != Scope.USER:
        return ""
    if user is None or not getattr(user, "pk", None):
        return ""
    return str(user.pk)


def get_preference(key, user=None):
    definition = PREFERENCES.get(key)
    value = (
        Preference.objects.filter(
            scope=definition.scope,
            scope_id=resolve_scope_id(definition, user),
            key=definition.key,
        )
        .values_list("value", flat=True)
        .first()
    )
    if value is None:
        return definition.default
    return definition.deserialize(value)


def get_preferences(keys, user=None) -> dict:
    definitions = [PREFERENCES.get(key) for key in keys]
    if not definitions:
        return {}

    lookup = Q()
    for definition in definitions:
        lookup |= Q(
            scope=definition.scope,
            scope_id=resolve_scope_id(definition, user),
            key=definition.key,
        )

    rows = {
        (row.scope, row.scope_id, row.key): row.value
        for row in Preference.objects.filter(lookup)
    }

    values = {}
    for definition in definitions:
        row_key = (
            definition.scope,
            resolve_scope_id(definition, user),
            definition.key,
        )
        values[definition.key] = (
            definition.deserialize(rows[row_key])
            if row_key in rows
            else definition.default
        )
    return values


def get_category_preferences(category, user=None) -> dict:
    definitions = PREFERENCES.by_category(category)
    return get_preferences([definition.key for definition in definitions], user=user)


def set_preference(key, value, user=None):
    definition = PREFERENCES.get(key)
    value = definition.clean(value)
    Preference.objects.update_or_create(
        scope=definition.scope,
        scope_id=resolve_scope_id(definition, user),
        key=definition.key,
        defaults={"value": definition.serialize(value)},
    )
    return value
