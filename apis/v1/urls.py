from django.urls import path

from apis.v1.account.view import PasswordView
from apis.v1.appointments.views.appointment import AppointmentView
from apis.v1.appointments.views.appointments import AppointmentsView
from apis.v1.catalogs.registry import catalog_urlpatterns
from apis.v1.clients.view import ClientsView, ClientView
from apis.v1.docs.view import DocsView, SchemaView
from apis.v1.home.view import HomeView
from apis.v1.me.view import MeView, PreferencesView, ProfileView
from apis.v1.services.views.categories import CategoriesView, CategoryView
from apis.v1.services.views.services import ServicesView, ServiceView
from apis.v1.session.view import BiometricView, LoginView, LogoutView, RefreshView
from apis.v1.startup.view import StartupView
from apis.v1.sync.view import ChangesView

urlpatterns = [
    path("startup/", StartupView.as_view(), name="api_startup"),
    path("session/login/", LoginView.as_view(), name="api_session_login"),
    path("session/refresh/", RefreshView.as_view(), name="api_session_refresh"),
    path("session/biometric/", BiometricView.as_view(), name="api_session_biometric"),
    path("session/logout/", LogoutView.as_view(), name="api_session_logout"),
    path("account/password/", PasswordView.as_view(), name="api_account_password"),
    path("me/", MeView.as_view(), name="api_me"),
    path("me/profile/", ProfileView.as_view(), name="api_me_profile"),
    path("me/preferences/", PreferencesView.as_view(), name="api_me_preferences"),
    *catalog_urlpatterns(),
    path("home/", HomeView.as_view(), name="api_home"),
    path("sync/changes/", ChangesView.as_view(), name="api_sync_changes"),
    path("clients/", ClientsView.as_view(), name="api_clients"),
    path("clients/<int:pk>/", ClientView.as_view(), name="api_client"),
    path("appointments/", AppointmentsView.as_view(), name="api_appointments"),
    path("appointments/<int:pk>/", AppointmentView.as_view(), name="api_appointment"),
    path("categories/", CategoriesView.as_view(), name="api_categories"),
    path("categories/<int:pk>/", CategoryView.as_view(), name="api_category"),
    path("services/", ServicesView.as_view(), name="api_services"),
    path("services/<int:pk>/", ServiceView.as_view(), name="api_service"),
    path("schema/", SchemaView.as_view(), name="api_schema"),
    path("docs/", DocsView.as_view(), name="api_docs"),
]
