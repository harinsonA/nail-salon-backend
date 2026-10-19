from apps.seguridad.access import register_login


def reset_failures_on_login(sender, request, user, **kwargs):
    register_login(user)
