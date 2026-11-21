from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.messages import (
    DISCOUNT_INVALID,
    MAX_QUANTITY,
    QUANTITY_INVALID,
    SERVICE_REPEATED,
    SERVICE_UNAVAILABLE,
    SERVICES_INVALID,
    SERVICES_REQUIRED,
)
from apps.payments.accounting import ServiceLines
from apps.services.models import Servicio


class AppointmentServices:
    FIELD = "services"

    def __init__(self, details=None):
        self.details = details or {}

    @classmethod
    def for_appointment(cls, appointment):
        if appointment is None:
            return cls()
        return cls({detail.pk: detail for detail in appointment.detalles.all()})

    @classmethod
    def error(cls, message):
        return AppointmentRuleError(message, cls.FIELD)

    def clean(self, lines):
        resolved = self.resolve(self.checked(lines))
        keys = [
            (
                service.pk if service else None,
                detail.pk if detail and not service else None,
            )
            for _, detail, service in resolved
        ]
        if len(set(keys)) != len(keys):
            raise self.error(SERVICE_REPEATED)
        return [
            self.clean_line(line, detail, service)
            for line, detail, service in resolved
        ]

    def checked(self, lines):
        if not isinstance(lines, list):
            raise self.error(SERVICES_INVALID)
        if not all(isinstance(line, dict) for line in lines):
            raise self.error(SERVICES_INVALID)
        if not lines:
            raise self.error(SERVICES_REQUIRED)
        return lines

    def resolve(self, lines):
        new_ids = []
        resolved = []
        try:
            for line in lines:
                if line.get("detalle") is not None:
                    detail = self.details.get(int(line["detalle"]))
                    if not detail:
                        raise self.error(SERVICES_INVALID)
                    resolved.append((line, detail, detail.servicio))
                else:
                    new_ids.append(int(line.get("id")))
                    resolved.append((line, None, new_ids[-1]))
        except (TypeError, ValueError) as error:
            raise self.error(SERVICES_INVALID) from error
        services = Servicio.activos.in_bulk(new_ids)
        if len(services) != len(set(new_ids)):
            raise self.error(SERVICE_UNAVAILABLE)
        return [
            (line, detail, service if detail else services[service])
            for line, detail, service in resolved
        ]

    @classmethod
    def quoted_price(cls, line):
        quoted = line.get("precio")
        if quoted is None:
            return None
        if isinstance(quoted, bool) or not isinstance(quoted, int) or quoted < 0:
            raise cls.error(SERVICES_INVALID)
        return quoted

    @classmethod
    def clean_line(cls, line, detail, service):
        name = detail.nombre_servicio if detail else service.nombre
        quoted = None if detail else cls.quoted_price(line)
        if detail:
            price = detail.precio_servicio
        elif quoted is None:
            price = service.precio
        else:
            price = min(service.precio, quoted)
        try:
            quantity = int(line.get("cantidad", 1))
            discount = int(line.get("descuento", 0))
        except (TypeError, ValueError) as error:
            raise cls.error(SERVICES_INVALID) from error
        if not 1 <= quantity <= MAX_QUANTITY:
            raise cls.error(QUANTITY_INVALID.format(name=name, max=MAX_QUANTITY))
        if not ServiceLines.accepts_discount(price, quantity, discount):
            raise cls.error(DISCOUNT_INVALID.format(name=name))
        return {
            "detail": detail,
            "service": service,
            "quantity": quantity,
            "discount": discount,
            "price": price,
            "quoted": quoted,
            "total": ServiceLines.total(price, quantity, discount),
        }

    @staticmethod
    def total(lines):
        return sum(line["total"] for line in lines)

    @staticmethod
    def lowered(lines):
        return [
            line
            for line in lines
            if line["quoted"] is not None and line["price"] < line["quoted"]
        ]
