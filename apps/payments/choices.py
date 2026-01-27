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
