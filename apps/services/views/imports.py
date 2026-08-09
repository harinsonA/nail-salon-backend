from django.urls import reverse_lazy

from apps.common.imports.async_views import BaseAsyncImportView
from apps.common.imports.views import BaseExampleExportView
from apps.services.imports import (
    CategoryAsyncImportValidator,
    ServiceAsyncImportValidator,
)
from apps.services.tasks import import_categories, import_services


class ServiceImportView(BaseAsyncImportView):
    title = "Importación de servicios"
    validator_class = ServiceAsyncImportValidator
    view_url = reverse_lazy("service_import")
    example_export_url = reverse_lazy("service_example_export")
    back_url = reverse_lazy("services")

    import_task = import_services
    origin = "importacion_servicios"
    process_name = "Importación de servicios"


class ServiceExampleExportView(BaseExampleExportView):
    validator_class = ServiceAsyncImportValidator
    filename = "plantilla_servicios"
    example_rows = [
        [
            "Manicure Clásica",
            "1",
            "Esmaltado permanente con limado y cutícula",
            "15000",
            "30",
            "activo",
        ],
    ]


class CategoryImportView(BaseAsyncImportView):
    title = "Importación de categorías"
    validator_class = CategoryAsyncImportValidator
    view_url = reverse_lazy("category_import")
    example_export_url = reverse_lazy("category_example_export")
    back_url = reverse_lazy("categories")

    import_task = import_categories
    origin = "importacion_categorias"
    process_name = "Importación de categorías"


class CategoryExampleExportView(BaseExampleExportView):
    validator_class = CategoryAsyncImportValidator
    filename = "plantilla_categorias"
    example_rows = [
        [
            "Manicure",
            "Servicios de manicure y esmaltado",
            "activo",
        ],
    ]
