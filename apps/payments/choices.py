# Constantes para choices de modelos


class EstadoCita:
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    COMPLETADA = "COMPLETADA"

    CHOICES = [
        (PENDIENTE, "Pendiente"),
        (CONFIRMADA, "Confirmada"),
        (CANCELADA, "Cancelada"),
        (COMPLETADA, "Completada"),
    ]


class MetodoPago:
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"

    CHOICES = [
        (EFECTIVO, "Efectivo"),
        (TARJETA, "Tarjeta"),
        (TRANSFERENCIA, "Transferencia"),
        (CHEQUE, "Cheque"),
    ]


class EstadoPago:
    PENDIENTE = "PENDIENTE"
    COMPLETADO = "COMPLETADO"
    REEMBOLSADO = "REEMBOLSADO"
    IMPAGO = "IMPAGO"

    CHOICES = [
        (PENDIENTE, "Pendiente"),
        (COMPLETADO, "Completado"),
        (REEMBOLSADO, "Reembolsado"),
        (IMPAGO, "Impago"),
    ]


class TipoDetallePago:
    RESERVA = "RESERVA"
    ANTICIPO = "ANTICIPO"
    ABONO = "ABONO"
    DEVOLUCION = "DEVOLUCION"

    CHOICES = [
        (RESERVA, "Reserva"),
        (ANTICIPO, "Anticipo"),
        (ABONO, "Abono"),
        (DEVOLUCION, "Devolución"),
    ]


class EstadoDetallePago:
    VIGENTE = "VIGENTE"
    RETENIDO = "RETENIDO"
    RETENIDO_DEFINITIVO = "RETENIDO_DEFINITIVO"
    DEVUELTO = "DEVUELTO"

    CHOICES = [
        (VIGENTE, "Vigente"),
        (RETENIDO, "Retenido"),
        (RETENIDO_DEFINITIVO, "Retenido definitivo"),
        (DEVUELTO, "Devuelto"),
    ]
