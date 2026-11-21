from apps.services.editing import CategoryInitial
from apps.services.models import Categoria

FORM_FIELDS = {
    "nombre": "name",
    "descripcion": "description",
}
API_FIELDS = {form_field: field for field, form_field in FORM_FIELDS.items()}


class CategoryFormData:
    @staticmethod
    def for_create(changes: dict) -> dict:
        data = {form_field: changes.get(field) or "" for field, form_field in FORM_FIELDS.items()}
        return {**data, "status": True}

    @staticmethod
    def for_update(category: Categoria, changes: dict) -> dict:
        current = CategoryInitial.of(category)
        data = {
            form_field: (changes[field] if field in changes else current.get(form_field)) or ""
            for field, form_field in FORM_FIELDS.items()
        }
        estado = changes.get("estado", category.estado)
        return {**data, "status": estado == Categoria.EstadoChoices.ACTIVO}

    @staticmethod
    def errors(form) -> dict:
        return {API_FIELDS.get(name, name): messages for name, messages in form.errors.items()}
