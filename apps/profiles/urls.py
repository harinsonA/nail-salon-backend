from django.urls import path
from apps.profiles.views.cambiar_clave.view import CambiarClaveView
from apps.profiles.views.equipo.view import (
    MemberActiveModalView,
    MemberCreateModalView,
    MemberPasswordResetModalView,
    MemberUnlockModalView,
    MemberUpdateModalView,
    TeamListView,
    TeamView,
)
from apps.profiles.views.login.view import LoginView, LogoutView
from apps.profiles.views.profile.view import ProfileModalView
from apps.profiles.views.session.view import SessionPingView

urlpatterns = [
    path("inicio_sesion/", LoginView.as_view(), name="login"),
    path("cerrar_sesion/", LogoutView.as_view(), name="logout"),
    path("cambiar_clave/", CambiarClaveView.as_view(), name="cambiar_clave"),
    path("Perfil/", ProfileModalView.as_view(), name="profile_modal"),
    path("sesion/ping/", SessionPingView.as_view(), name="session_ping"),
    path("equipo/", TeamView.as_view(), name="equipo"),
    path("equipo/lista/ajax", TeamListView.as_view(), name="equipo_lista"),
    path("equipo/crear/", MemberCreateModalView.as_view(), name="equipo_crear"),
    path("equipo/<int:pk>/editar/", MemberUpdateModalView.as_view(), name="equipo_editar"),
    path("equipo/<int:pk>/activar/", MemberActiveModalView.as_view(), name="equipo_activar"),
    path("equipo/<int:pk>/restablecer-clave/", MemberPasswordResetModalView.as_view(), name="equipo_restablecer_clave"),
    path("equipo/<int:pk>/desbloquear/", MemberUnlockModalView.as_view(), name="equipo_desbloquear"),
]
