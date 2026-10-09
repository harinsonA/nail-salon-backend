from django_tenants.utils import get_public_schema_name, schema_exists

from apps.tenancy.models import Negocio


def clasificar_negocios():
    listos, omitidos = [], []
    negocios = Negocio.objects.exclude(schema_name=get_public_schema_name()).order_by("schema_name")
    for esquema, estado in negocios.values_list("schema_name", "estado"):
        if estado != Negocio.Estado.PREPARANDO and schema_exists(esquema):
            listos.append(esquema)
        else:
            omitidos.append(esquema)
    return listos, omitidos
