from django.urls import path
from apps.profiles.views.login.view import LoginView, LogoutView
from apps.profiles.views.profile.view import ProfileModalView
from apps.profiles.views.session.view import SessionPingView

urlpatterns = [
    path("inicio_sesion/", LoginView.as_view(), name="login"),
    path("cerrar_sesion/", LogoutView.as_view(), name="logout"),
    path("Perfil/", ProfileModalView.as_view(), name="profile_modal"),
    path("sesion/ping/", SessionPingView.as_view(), name="session_ping"),
]
