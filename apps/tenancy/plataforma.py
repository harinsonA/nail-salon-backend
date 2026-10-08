from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio


def asegurar_negocio_publico():
    return Negocio.objects.get_or_create(
        schema_name=get_public_schema_name(),
        defaults={"nombre": "Hi Agenda", "estado": Negocio.Estado.ACTIVO},
    )


def asegurar_dominio(dominio, negocio, es_principal=False):
    existente = Dominio.objects.filter(domain=dominio).first()
    if existente is None:
        Dominio.objects.create(domain=dominio, tenant=negocio, is_primary=es_principal)
        return "creado"
    if existente.tenant_id != negocio.pk:
        return "ya apunta a otro negocio, no se cambió"
    return "ya existía"
