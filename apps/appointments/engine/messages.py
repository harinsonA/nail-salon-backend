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
