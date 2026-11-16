from django.contrib.auth.forms import SetPasswordForm

from apps.profiles.models import Perfil

CURRENT_FIELD = "current_password"
NEW_FIELD = "new_password"
CONFIRM_FIELD = "confirm_password"

TEMPORARY_FIELDS = {"new_password1": NEW_FIELD, "new_password2": CONFIRM_FIELD}


class PasswordChange:
    def __init__(self, user):
        self.user = user

    def voluntary_errors(self, current, new, confirm):
        errors = {}
        if not (new or confirm or current):
            return errors
        if not current:
            errors[CURRENT_FIELD] = ["Debes ingresar tu contraseña actual."]
        elif not self.user.check_password(current):
            errors[CURRENT_FIELD] = ["La contraseña actual es incorrecta."]
        if not new:
            errors[NEW_FIELD] = ["Debes ingresar la nueva contraseña."]
        if not confirm:
            errors[CONFIRM_FIELD] = ["Debes confirmar la nueva contraseña."]
        if new and confirm and new != confirm:
            errors[CONFIRM_FIELD] = ["Las contraseñas no coinciden."]
        return errors

    def temporary_form(self, new, confirm):
        return SetPasswordForm(self.user, data={"new_password1": new, "new_password2": confirm})

    def temporary_errors(self, form):
        return {
            TEMPORARY_FIELDS.get(field, field): [str(error) for error in errors]
            for field, errors in form.errors.items()
        }

    def change(self, current, new, confirm, temporary):
        if temporary:
            form = self.temporary_form(new, confirm)
            if not form.is_valid():
                return self.temporary_errors(form)
            form.save()
            self.finish_temporary()
            return {}
        errors = self.voluntary_errors(current, new, confirm)
        if not new and not errors:
            errors[NEW_FIELD] = ["Debes ingresar la nueva contraseña."]
        if errors:
            return errors
        self.user.set_password(new)
        self.user.save(update_fields=["password"])
        return {}

    def finish_temporary(self):
        Perfil.objects.update_or_create(user=self.user, defaults={"debe_cambiar_clave": False})
