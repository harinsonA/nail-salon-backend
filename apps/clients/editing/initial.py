from apps.clients.models import Cliente
from apps.common.utils.countries.constants import CountryPhonePrefix

from .form import ClientsForm


class ClientInitial:
    @staticmethod
    def phone_and_prefix(client: Cliente) -> tuple:
        if not client.telefono:
            return CountryPhonePrefix.CHILE, ""
        for prefix in dict(CountryPhonePrefix.choices):
            if client.telefono.startswith(prefix):
                return prefix, client.telefono[len(prefix) :]
        return "", ""

    @classmethod
    def of(cls, client: Cliente) -> dict:
        prefix, phone = cls.phone_and_prefix(client)
        return {
            **ClientsForm.split_names_initial(client.nombre, client.apellido),
            **ClientsForm.national_id_initial(client),
            "country_phone_prefix": prefix,
            "phone": phone,
            "email": client.email,
            "status": client.estado == Cliente.EstadoChoices.ACTIVO,
            "notes": client.notas,
        }
