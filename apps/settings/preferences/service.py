from django.db import connection
from django.db.models import Q
from django_tenants.utils import get_public_schema_name, schema_context

from apps.settings.preferences.constants import Scope
from apps.settings.preferences.models import Preference
from apps.settings.preferences.registry import PREFERENCES


def resolve_scope_id(definition, user) -> str:
    if definition.scope != Scope.USER:
        return ""
    if user is None or not getattr(user, "pk", None):
        return ""
    return str(user.pk)


def fuera_de_un_negocio() -> bool:
    return connection.schema_name == get_public_schema_name()


def is_platform(definition) -> bool:
    return definition.scope == Scope.PLATAFORMA


def read_values(definitions, user) -> dict:
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


def get_preference(key, user=None):
    definition = PREFERENCES.get(key)
    return get_preferences([definition], user=user)[definition.key]


def get_preferences(keys, user=None) -> dict:
    definitions = [PREFERENCES.get(key) for key in keys]
    if not definitions:
        return {}

    platform = [definition for definition in definitions if is_platform(definition)]
    schema = [definition for definition in definitions if not is_platform(definition)]

    values = {}
    if platform:
        with schema_context(get_public_schema_name()):
            values.update(read_values(platform, user))
    if schema and fuera_de_un_negocio():
        values.update({definition.key: definition.default for definition in schema})
    elif schema:
        values.update(read_values(schema, user))
    return {definition.key: values[definition.key] for definition in definitions}


def set_platform_value(definition, value):
    from_negocio = not fuera_de_un_negocio()
    with schema_context(get_public_schema_name()):
        preference = Preference.objects.filter(
            scope=definition.scope, scope_id="", key=definition.key
        ).first() or Preference(scope=definition.scope, scope_id="", key=definition.key)
        preference.value = definition.serialize(value)
        if from_negocio:
            preference._history_user = None
        preference.save()


def set_preference(key, value, user=None):
    definition = PREFERENCES.get(key)
    value = definition.clean(value)
    if is_platform(definition):
        set_platform_value(definition, value)
        return value
    Preference.objects.update_or_create(
        scope=definition.scope,
        scope_id=resolve_scope_id(definition, user),
        key=definition.key,
        defaults={"value": definition.serialize(value)},
    )
    return value
