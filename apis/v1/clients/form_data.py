from apps.clients.editing import ClientInitial
from apps.clients.models import Cliente

FORM_FIELDS = {
    "first_name": "first_name",
    "second_name": "second_name",
    "first_surname": "first_surname",
    "second_surname": "second_surname",
    "phone_prefix": "country_phone_prefix",
    "phone": "phone",
    "email": "email",
    "pais": "national_id_country",
    "tipo_identificador_nacional": "national_id_type",
    "identificador_nacional": "national_id",
    "notas": "notes",
}
API_FIELDS = {form_field: field for field, form_field in FORM_FIELDS.items()}


class ClientFormData:
    @staticmethod
    def for_create(changes: dict) -> dict:
        data = {form_field: changes.get(field) or "" for field, form_field in FORM_FIELDS.items()}
        return {**data, "status": True}

    @staticmethod
    def for_update(client: Cliente, changes: dict) -> dict:
        current = ClientInitial.of(client)
        data = {
            form_field: (changes[field] if field in changes else current.get(form_field)) or ""
            for field, form_field in FORM_FIELDS.items()
        }
        estado = changes.get("estado", client.estado)
        return {**data, "status": estado == Cliente.EstadoChoices.ACTIVO}

    @staticmethod
    def errors(form) -> dict:
        return {API_FIELDS.get(name, name): messages for name, messages in form.errors.items()}
