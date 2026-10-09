from django.contrib import admin

from .negocio import NegocioAdmin
from .persona import PersonaAdmin
from .rubro import RubroAdmin

admin.site.site_header = "Hi Agenda · Panel"
admin.site.site_title = "Hi Agenda · Panel"
admin.site.index_title = "Negocios y titulares"

__all__ = ["NegocioAdmin", "PersonaAdmin", "RubroAdmin"]
