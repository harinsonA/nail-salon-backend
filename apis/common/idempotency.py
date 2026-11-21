import json
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from apps.seguridad.models import ClaveIdempotencia


class IdempotentWrite:
    HEADER = "Idempotency-Key"
    MAX_LENGTH = 64
    KEEP_DAYS = 30

    def __init__(self, request):
        self.request = request
        self.key = request.headers.get(self.HEADER) or ""

    @property
    def usable(self):
        return 0 < len(self.key) <= self.MAX_LENGTH

    def stored(self):
        return ClaveIdempotencia.objects.filter(
            user=self.request.user,
            clave=self.key,
            metodo=self.request.method,
            ruta=self.request.path,
        ).first()

    def remember(self, response):
        if not 200 <= response.status_code < 300:
            return
        ClaveIdempotencia.objects.filter(
            user=self.request.user,
            created__lt=timezone.now() - timedelta(days=self.KEEP_DAYS),
        ).delete()
        try:
            with transaction.atomic():
                ClaveIdempotencia.objects.create(
                    user=self.request.user,
                    clave=self.key,
                    metodo=self.request.method,
                    ruta=self.request.path,
                    codigo_respuesta=response.status_code,
                    respuesta=json.loads(JSONRenderer().render(response.data)),
                )
        except IntegrityError:
            pass

    def run(self, handler):
        if not self.usable:
            return handler()
        previous = self.stored()
        if previous:
            return Response(previous.respuesta, status=previous.codigo_respuesta)
        response = handler()
        self.remember(response)
        return response
