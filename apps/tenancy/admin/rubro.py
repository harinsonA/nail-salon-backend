from django.contrib import admin

from apps.tenancy.models import Rubro


@admin.register(Rubro)
class RubroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo", "activo", "orden")
    list_editable = ("activo", "orden")
    search_fields = ("nombre", "codigo")
