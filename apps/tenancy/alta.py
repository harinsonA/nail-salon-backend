from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction

from apps.common.claves import generar_clave_temporal
from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo, PersonaTelefono
from apps.tenancy.subdominios import esquema_desde_subdominio


def dominio_de(subdominio):
    return f"{subdominio}.{settings.DOMINIO_BASE}"


def dar_de_alta(datos, creado_por):
    from apps.tenancy.tasks import preparar_negocio

    clave = generar_clave_temporal()
    with transaction.atomic():
        titular = datos.get("titular") or crear_persona(datos)
        registrar_correo(titular, datos["correo"])
        negocio = Negocio(
            schema_name=esquema_desde_subdominio(datos["subdominio"]),
            nombre=datos["nombre"],
            titular=titular,
            rubro=datos.get("rubro"),
            zona_horaria=datos["zona_horaria"],
            creado_por=creado_por,
            estado=Negocio.Estado.PREPARANDO,
        )
        negocio._change_reason = "Alta desde el panel"
        negocio.save()
        Dominio.objects.create(domain=dominio_de(datos["subdominio"]), tenant=negocio, is_primary=True)
        hash_clave = make_password(clave)
        transaction.on_commit(lambda: preparar_negocio.delay(negocio.pk, datos["correo"], hash_clave))
    return negocio, clave


def crear_persona(datos):
    persona = Persona.objects.create(nombres=datos["nombres"], apellidos=datos.get("apellidos", ""))
    if datos.get("telefono"):
        PersonaTelefono.objects.create(
            persona=persona,
            codigo_pais=datos["codigo_pais"],
            numero=datos["telefono"],
            es_principal=True,
        )
    return persona


def registrar_correo(persona, correo):
    if persona.correos.filter(correo=correo).exists():
        return
    PersonaCorreo.objects.create(
        persona=persona,
        correo=correo,
        etiqueta="acceso",
        es_principal=not persona.correos.exists(),
    )


def correo_de_acceso(persona):
    correos = persona.correos.all()
    elegido = (
        correos.filter(etiqueta="acceso").order_by("-created").first()
        or correos.filter(es_principal=True).first()
        or correos.order_by("created").first()
    )
    return elegido.correo if elegido else None


def url_en_dominio(request, dominio, ruta="/"):
    _, separador, puerto = request.get_host().rpartition(":")
    sufijo = f":{puerto}" if separador and puerto.isdigit() else ""
    return f"{request.scheme}://{dominio}{sufijo}{ruta}"
