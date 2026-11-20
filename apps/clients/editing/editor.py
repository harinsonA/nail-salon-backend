from apps.clients.models import Cliente

from .form import ClientsForm


class ClientEditor:
    CREATED_MESSAGE = "Cliente %(client_full_name)s creado exitosamente."
    UPDATED_MESSAGE = "Cliente %(client_full_name)s actualizado exitosamente."

    @staticmethod
    def create(form: ClientsForm, **extra) -> Cliente:
        return Cliente.objects.create(**form.cleaned_data, **extra)

    @staticmethod
    def update(client: Cliente, form: ClientsForm) -> Cliente:
        cleaned_data = form.cleaned_data
        for field, value in cleaned_data.items():
            setattr(client, field, value)
        client.save(update_fields=cleaned_data.keys())
        return client

    @classmethod
    def created_message(cls, client: Cliente) -> str:
        return cls.CREATED_MESSAGE % {"client_full_name": client.nombre_completo}

    @classmethod
    def updated_message(cls, client: Cliente) -> str:
        return cls.UPDATED_MESSAGE % {"client_full_name": client.nombre_completo}
