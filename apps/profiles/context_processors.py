from apps.profiles.permisos import administra_el_negocio


def permisos(request):
    usuario = getattr(request, "user", None)
    return {"administra_el_negocio": bool(usuario) and administra_el_negocio(usuario)}
