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
    PAGADO = "PAGADO"
    PENDIENTE = "PENDIENTE"
    CANCELADO = "CANCELADO"

    CHOICES = [
        (PAGADO, "Pagado"),
        (PENDIENTE, "Pendiente"),
        (CANCELADO, "Cancelado"),
    ]
