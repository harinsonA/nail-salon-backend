from apps.services.editing import ServiceEditor, ServiceInitial
from apps.services.models import Servicio

FORM_FIELDS = {
    "categoria_id": "category",
    "nombre": "name",
    "precio": "price",
    "duracion_estimada": "duration",
    "descripcion": "description",
}
API_FIELDS = {form_field: field for field, form_field in FORM_FIELDS.items()}


class ServiceFormData:
    @staticmethod
    def value(value):
        return "" if value is None else value

    @classmethod
    def for_create(cls, changes: dict) -> dict:
        data = {form_field: cls.value(changes.get(field)) for field, form_field in FORM_FIELDS.items()}
        return {**data, "status": True}

    @classmethod
    def current(cls, service: Servicio) -> dict:
        initial = ServiceInitial.of(service)
        return {**initial, "price": int(service.precio or 0)}

    @classmethod
    def for_update(cls, service: Servicio, changes: dict) -> dict:
        current = cls.current(service)
        data = {
            form_field: cls.value(changes[field] if field in changes else current.get(form_field))
            for field, form_field in FORM_FIELDS.items()
        }
        estado = changes.get("estado", service.estado)
        return {**data, "status": estado == Servicio.EstadoChoices.ACTIVO}

    @staticmethod
    def errors(form) -> dict:
        return {API_FIELDS.get(name, name): messages for name, messages in form.errors.items()}

    @staticmethod
    def category_error(message: str) -> dict:
        return {API_FIELDS[ServiceEditor.CATEGORY_FIELD]: [message]}
