from django.urls import path
from apps.services.views.servicio import (
    ServicesView,
    ServiceListView,
    ServiceCreateModalView,
    ServiceDetailModalView,
    ServiceDeleteModalView,
)

urlpatterns = [
    path(
        "servicios/",
        ServicesView.as_view(),
        name="services",
    ),
    path(
        "servicios/lista/ajax",
        ServiceListView.as_view(),
        name="service_list",
    ),
    path(
        "servicios/crear/",
        ServiceCreateModalView.as_view(),
        name="service_create_modal",
    ),
    path(
        "servicios/<int:pk>/detalle/",
        ServiceDetailModalView.as_view(),
        name="service_detail_modal",
    ),
    path(
        "servicios/<int:pk>/eliminar/",
        ServiceDeleteModalView.as_view(),
        name="service_delete_modal",
    ),
]
