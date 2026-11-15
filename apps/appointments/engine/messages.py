MAX_QUANTITY = 99
REFERENCE_MAX_LENGTH = 100
SERVICES_REQUIRED = "Agrega al menos un servicio."
SERVICES_INVALID = "Los servicios enviados no son válidos."
SERVICE_UNAVAILABLE = "Uno de los servicios ya no está disponible."
SERVICE_REPEATED = "Un servicio no puede repetirse en la misma cita."
QUANTITY_INVALID = "La cantidad de «{name}» debe estar entre 1 y {max}."
DISCOUNT_INVALID = (
    "El descuento de «{name}» no puede ser negativo ni superar su precio."
)
ADVANCES_INVALID = "Los anticipos enviados no son válidos."
ADVANCE_AMOUNT_REQUIRED = "Ingresa el monto de cada anticipo."
ADVANCE_LOCKED_ROLE = (
    "Solo la propietaria o la encargada pueden cambiar anticipos ya registrados."
)
ADVANCES_TOO_HIGH = (
    "Los anticipos suman {paid} y no pueden superar el total de los servicios "
    "({total})."
)
RESERVATION_INVALID = "La reserva enviada no es válida."
RESERVATION_LOCKED_ROLE = (
    "Solo la propietaria o la encargada pueden cambiar o quitar una reserva guardada."
)
RESERVATION_TOO_HIGH = (
    "La reserva o los anticipos suman {paid} y no pueden superar el total de los "
    "servicios ({total})."
)
FULL_PAYMENT_LABEL = "Paga el total ahora"
BALANCE_PAYMENT_LABEL = "Paga el saldo ahora"
AMOUNT_TOO_HIGH = 'Si paga {total} o más, activa "{label}".'
SETTLED_SUBJECTS = {
    ("Anticipo",): "El anticipo ya cubre",
    ("Reserva",): "La reserva ya cubre",
    ("Reserva", "Anticipo"): "La reserva y el anticipo ya cubren",
}
SETTLED_HINT = (
    "{subject} el total de la cita. Al completarla queda pagada y hoy no hay nada "
    "que cobrar."
)
NOTHING_TO_CHARGE = "La cita no tiene monto por cobrar. Al completarla queda pagada."
PREPAID_TOO_HIGH = (
    "Lo pagado antes ({paid}) supera el total de los servicios ({total}). "
    "Edita la cita antes de completarla."
)
COMPLETE_NOT_PENDING = "Solo se pueden completar las citas en estado Pendiente."
REFUNDS_INVALID = "Los reembolsos enviados no son válidos."
CANCEL_NOT_PENDING = "Solo se pueden cancelar las agendas en estado Pendiente."
RESTORED_INVALID = "Los pagos a restaurar no son válidos."
RESTORE_NOT_CANCELLED = "Solo se pueden restaurar las agendas en estado Cancelada."
