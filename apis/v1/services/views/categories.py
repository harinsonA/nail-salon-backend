from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.views import ApiView
from apis.v1.services.form_data import CategoryFormData
from apis.v1.services.serializers import (
    CategoryFieldsSerializer,
    CategorySavedSerializer,
    CategoryUpdateSerializer,
)
from apps.services.editing import CategoriesForm, CategoryEditor
from apps.services.models import Categoria

"""========================================================================="""
# region ........ Helpers


def valid_form(data):
    form = CategoriesForm(data=data)
    if not form.is_valid():
        raise serializers.ValidationError(CategoryFormData.errors(form))
    return form


def saved_response(message, category, status_code=status.HTTP_200_OK):
    return Response(
        CategorySavedSerializer({"message": message, "category": category}).data,
        status=status_code,
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class CategoriesView(ApiView):
    http_method_names = ["post"]

    @extend_schema(
        summary="Crear categoría",
        description="Mismo formulario y validaciones de la web; nace activa. Solo administración.",
        request=CategoryFieldsSerializer,
        responses={201: CategorySavedSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = CategoryFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = valid_form(CategoryFormData.for_create(serializer.validated_data))
        category = CategoryEditor.create(form)
        return saved_response(
            CategoryEditor.created_message(category), category, status.HTTP_201_CREATED
        )


class CategoryView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar categoría",
        description=(
            "Solo lo que cambió, incluido estado. Al inactivarla también se inactivan sus "
            "servicios, como en la web. Con version distinta al modified responde 409."
        ),
        request=CategoryUpdateSerializer,
        responses=CategorySavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        category = Categoria.objects.filter(pk=kwargs["pk"]).first()
        if category is None:
            raise NotFound(messages.CATEGORY_NOT_FOUND)
        serializer = CategoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        version = changes.get("version")
        if version and version != category.modified:
            raise errors.Conflict(messages.CATEGORY_CHANGED)
        form = valid_form(CategoryFormData.for_update(category, changes))
        category = CategoryEditor.update(category, form)
        return saved_response(CategoryEditor.updated_message(category), category)


# endregion
"""========================================================================="""
