from django.db import transaction

from apps.appointments.models import Cita, DetalleCita
from apps.payments.accounting import AppointmentPaymentService


class AppointmentWriter:
    DETAIL_FIELDS = ["cantidad_servicios", "descuento", "precio_acordado", "modified"]

    def __init__(self, user):
        self.user = user

    @staticmethod
    def build_detail(appointment, line):
        service = line["service"]
        return DetalleCita(
            cita=appointment,
            servicio=service,
            nombre_servicio=service.nombre,
            precio_servicio=service.precio,
            duracion_estimada_servicio=service.duracion_estimada,
            precio_acordado=line["total"],
            cantidad_servicios=line["quantity"],
            descuento=line["discount"],
        )

    @transaction.atomic
    def create(self, data):
        appointment = Cita.objects.create(
            cliente=data["client"],
            fecha_agenda=data["date"],
            hora_agenda=data["time"],
            estado=Cita.EstadoChoices.PENDIENTE,
            observaciones=data["observations"] or None,
            creado_por=self.user,
            asignado_a=data["assigned_to"],
        )
        DetalleCita.objects.bulk_create(
            self.build_detail(appointment, line) for line in data["services"]
        )
        self.save_payments(appointment, data)
        return appointment

    @transaction.atomic
    def update(self, appointment, data):
        appointment.cliente = data["client"]
        appointment.fecha_agenda = data["date"]
        appointment.hora_agenda = data["time"]
        appointment.observaciones = data["observations"] or None
        appointment.asignado_a = data["assigned_to"]
        appointment.save()
        kept = [line["detail"].pk for line in data["services"] if line["detail"]]
        appointment.detalles.exclude(pk__in=kept).delete()
        for line in data["services"]:
            detail = line["detail"]
            if not detail:
                self.build_detail(appointment, line).save()
                continue
            detail.cantidad_servicios = line["quantity"]
            detail.descuento = line["discount"]
            detail.precio_acordado = line["total"]
            detail.save(update_fields=self.DETAIL_FIELDS)
        self.save_payments(appointment, data)
        return appointment

    def save_payments(self, appointment, data):
        AppointmentPaymentService(appointment, self.user).save_payments(
            data["advances"], data["reservation"]
        )
