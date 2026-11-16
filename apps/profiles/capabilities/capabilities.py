from apps.appointments.engine.assignment import AppointmentAssignment
from apps.profiles.permisos import (
    SOLO_ADMINISTRACION,
    SOLO_CON_EQUIPO,
    administra_el_negocio,
)
from apps.tenancy.user_limit import UserLimit


class Capabilities:
    BY_ROUTE = {
        "view_dashboard": "dashboard",
        "manage_services": "services",
        "manage_categories": "categories",
        "view_payments": "payments",
        "view_incomes": "incomes",
        "view_debtors": "debtors",
        "manage_team": "equipo",
        "manage_appointment_settings": "appointment_preferences",
    }
    VIEW_ALL_APPOINTMENTS = "view_all_appointments"
    ASSIGN_APPOINTMENTS = "assign_appointments"

    def __init__(self, user, negocio):
        self.user = user
        self.negocio = negocio
        self.assignment = AppointmentAssignment(user)

    def allows(self, url_name):
        if url_name in SOLO_ADMINISTRACION and not administra_el_negocio(self.user):
            return False
        if url_name in SOLO_CON_EQUIPO and not UserLimit(self.negocio).team_enabled:
            return False
        return True

    def as_list(self):
        capabilities = [
            capability
            for capability, url_name in self.BY_ROUTE.items()
            if self.allows(url_name)
        ]
        if not self.assignment.collaborator:
            capabilities += [self.VIEW_ALL_APPOINTMENTS, self.ASSIGN_APPOINTMENTS]
        return capabilities

    def assignable_users(self):
        if self.assignment.collaborator:
            return []
        return list(self.assignment.staff())
