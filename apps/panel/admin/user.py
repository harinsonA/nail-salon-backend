from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.panel.deletion import CurrentSchemaDeletionMixin

User = get_user_model()

admin.site.unregister(User)


@admin.register(User)
class UserAdmin(CurrentSchemaDeletionMixin, DjangoUserAdmin):
    pass
