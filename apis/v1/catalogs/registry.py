from django.urls import path

from apis.v1.catalogs.views import CountriesView, PaymentMethodsView, PhonePrefixesView

CATALOG_VIEWS = (
    CountriesView,
    PhonePrefixesView,
    PaymentMethodsView,
)


def catalog_urlpatterns():
    return [path(view.route(), view.as_view(), name=view.route_name()) for view in CATALOG_VIEWS]
