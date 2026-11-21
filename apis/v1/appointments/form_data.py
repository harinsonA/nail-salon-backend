import json

FORM_FIELDS = {
    "cliente_id": "client",
    "asignado_a_id": "assigned_to",
    "fecha_agenda": "date",
    "hora_agenda": "time",
    "observaciones": "observations",
}
API_FIELDS = {form_field: field for field, form_field in FORM_FIELDS.items()}
API_FIELDS["__all__"] = "non_field_errors"


class AppointmentFormData:
    @staticmethod
    def line(line):
        data = {
            "cantidad": line.get("cantidad_servicios", 1),
            "descuento": line.get("descuento", 0),
        }
        if line.get("detalle_id") is not None:
            return {**data, "detalle": line["detalle_id"]}
        return {**data, "id": line.get("servicio_id"), "precio": line.get("precio_servicio")}

    @staticmethod
    def advance(advance):
        if advance.get("id") is not None and advance.get("remove"):
            return {"id": advance["id"], "quitar": True}
        data = {
            "monto": advance.get("monto_pago"),
            "metodo": advance.get("metodo_pago"),
            "referencia": advance.get("referencia_pago") or "",
        }
        if advance.get("id") is not None:
            return {"id": advance["id"], **data}
        return data

    @staticmethod
    def reservation(reservation):
        if reservation is None:
            return ""
        return json.dumps(
            {
                "activa": reservation["active"],
                "metodo": reservation.get("metodo_pago"),
                "referencia": reservation.get("referencia_pago") or "",
            }
        )

    @classmethod
    def for_form(cls, changes: dict) -> dict:
        data = {
            form_field: changes.get(field) or "" for field, form_field in FORM_FIELDS.items()
        }
        return {
            **data,
            "services": json.dumps([cls.line(line) for line in changes.get("services", [])]),
            "advances": json.dumps([cls.advance(item) for item in changes.get("advances", [])]),
            "reservation": cls.reservation(changes.get("reservation")),
        }

    @staticmethod
    def errors(form) -> dict:
        return {API_FIELDS.get(name, name): messages for name, messages in form.errors.items()}
