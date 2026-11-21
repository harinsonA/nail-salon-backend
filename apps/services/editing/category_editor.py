from django.db import transaction
from django.utils import timezone

from apps.services.models import Categoria, Servicio

from .category_form import CategoriesForm


class CategoryEditor:
    CREATED_MESSAGE = "Categoria %(category_name)s creada exitosamente."
    UPDATED_MESSAGE = "Categoria %(category_name)s actualizada exitosamente."

    @staticmethod
    def create(form: CategoriesForm) -> Categoria:
        return Categoria.objects.create(**form.cleaned_data)

    @classmethod
    def update(cls, category: Categoria, form: CategoriesForm) -> Categoria:
        cleaned_data = form.cleaned_data
        previous_status = category.estado
        new_status = cleaned_data.get("estado", previous_status)
        with transaction.atomic():
            for field, value in cleaned_data.items():
                setattr(category, field, value)
            category.save(update_fields=cleaned_data.keys())
            cls.set_services_to_inactive_when_category_is_inactivated(
                category=category,
                previous_status=previous_status,
                new_status=new_status,
            )
        return category

    @staticmethod
    def set_services_to_inactive_when_category_is_inactivated(
        category: Categoria,
        previous_status: str,
        new_status: str,
    ):
        is_transition_to_inactive = (
            previous_status == Categoria.EstadoChoices.ACTIVO
            and new_status == Categoria.EstadoChoices.INACTIVO
        )
        if not is_transition_to_inactive:
            return

        category.servicios.filter(is_removed=False).exclude(
            estado=Servicio.EstadoChoices.INACTIVO
        ).update(estado=Servicio.EstadoChoices.INACTIVO, modified=timezone.now())

    @classmethod
    def created_message(cls, category: Categoria) -> str:
        return cls.CREATED_MESSAGE % {"category_name": category.nombre}

    @classmethod
    def updated_message(cls, category: Categoria) -> str:
        return cls.UPDATED_MESSAGE % {"category_name": category.nombre}
