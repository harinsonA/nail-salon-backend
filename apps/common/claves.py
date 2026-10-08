import secrets

ALFABETO_CLAVE = "abcdefghjkmnpqrstuvwxyz23456789"


def generar_clave_temporal():
    grupos = ("".join(secrets.choice(ALFABETO_CLAVE) for _ in range(4)) for _ in range(3))
    return "-".join(grupos)
