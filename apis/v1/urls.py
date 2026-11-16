from django.urls import path

from apis.v1.account.view import PasswordView
from apis.v1.docs.view import DocsView, SchemaView
from apis.v1.me.view import MeView, PreferencesView, ProfileView
from apis.v1.session.view import BiometricView, LoginView, LogoutView, RefreshView
from apis.v1.startup.view import StartupView

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
    path("schema/", SchemaView.as_view(), name="api_schema"),
    path("docs/", DocsView.as_view(), name="api_docs"),
]
