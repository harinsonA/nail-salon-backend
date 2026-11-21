from result import Err, Ok, Result

from apps.services.models import Categoria, Servicio

from .service_form import ServicesForm


class ServiceEditor:
    CREATED_MESSAGE = "Servicio %(service_name)s creado exitosamente."
    UPDATED_MESSAGE = "Servicio %(service_name)s actualizado exitosamente."
    INACTIVE_CATEGORY = "No puedes activar un servicio con una categoria inactiva."
    CATEGORY_FIELD = "category"

    @staticmethod
    def create(form: ServicesForm) -> Servicio:
        return Servicio.objects.create(**form.cleaned_data)

    @classmethod
    def update(cls, service: Servicio, form: ServicesForm) -> Result[Servicio, str]:
        cleaned_data = form.cleaned_data
        validation = cls.validate_category_active_for_activation(
            previous_status=service.estado,
            new_status=cleaned_data.get("estado", service.estado),
            category=cleaned_data.get("categoria"),
        )
        if validation.is_err():
            return validation
        for field, value in cleaned_data.items():
            setattr(service, field, value)
        service.save(update_fields=cleaned_data.keys())
        return Ok(service)

    @classmethod
    def validate_category_active_for_activation(
        cls,
        previous_status: str,
        new_status: str,
        category,
    ) -> Result[str, str]:
        is_transition_to_active = (
            previous_status == Servicio.EstadoChoices.INACTIVO
            and new_status == Servicio.EstadoChoices.ACTIVO
        )
        if not is_transition_to_active:
            return Ok("valid")

        is_category_active = category and category.estado == Categoria.EstadoChoices.ACTIVO
        if is_category_active:
            return Ok("valid")

        return Err(cls.INACTIVE_CATEGORY)

    @classmethod
    def created_message(cls, service: Servicio) -> str:
        return cls.CREATED_MESSAGE % {"service_name": service.nombre}

    @classmethod
    def updated_message(cls, service: Servicio) -> str:
        return cls.UPDATED_MESSAGE % {"service_name": service.nombre}
