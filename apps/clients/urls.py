from django.urls import path
from apps.clients.views.cliente import (
    ClientsView,
    ClientListView,
    ClientExportView,
    ClientCreateModalView,
    ClientDetailModalView,
    ClientDeleteModalView,
)
from apps.clients.views.imports import (
    ClientImportView,
    ClientExampleExportView,
)

urlpatterns = [
    path(
        "clientes/",
        ClientsView.as_view(),
        name="clients",
    ),
    path(
        "clientes/lista/ajax",
        ClientListView.as_view(),
        name="client_list",
    ),
    path(
        "clientes/exportar/",
        ClientExportView.as_view(),
        name="client_export",
    ),
    path(
        "clientes/importar/",
        ClientImportView.as_view(),
        name="client_import",
    ),
    path(
        "clientes/importar/plantilla/",
        ClientExampleExportView.as_view(),
        name="client_example_export",
    ),
    path(
        "clientes/crear/",
        ClientCreateModalView.as_view(),
        name="client_create_modal",
    ),
    path(
        "clientes/<int:pk>/detalle/",
        ClientDetailModalView.as_view(),
        name="client_detail_modal",
    ),
    path(
        "clientes/<int:pk>/eliminar/",
        ClientDeleteModalView.as_view(),
        name="client_delete_modal",
    ),
]
