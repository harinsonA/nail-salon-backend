from django_tenants.models import DomainMixin


class Dominio(DomainMixin):
    class Meta:
        db_table = "dominios"
        verbose_name = "Dominio"
        verbose_name_plural = "Dominios"
