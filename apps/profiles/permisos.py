from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil

ROLES_QUE_ADMINISTRAN = {Perfil.Rol.PROPIETARIO, Perfil.Rol.ENCARGADO}

SOLO_ADMINISTRACION = {
    "services",
    "service_list",
    "service_export",
    "service_import",
    "service_example_export",
    "service_create_modal",
    "service_detail_modal",
    "service_delete_modal",
    "categories",
    "category_list",
    "category_export",
    "category_import",
    "category_example_export",
    "category_create_modal",
    "category_detail_modal",
    "category_delete_modal",
    "payments",
    "payments_list",
    "payments_export",
    "payments_weekly_income_ajax",
    "incomes",
    "incomes_list",
    "incomes_export",
    "incomes_by_method_ajax",
    "debtors",
    "debtors_list",
    "debtors_export",
    "debt_detail_modal",
    "payment_detail_list",
    "add_payment_modal",
    "services_detail_list",
    "dashboard",
    "dashboard_attended_clients_ajax",
    "dashboard_income_ajax",
    "dashboard_appointment_status_ajax",
    "dashboard_payment_methods_ajax",
    "dashboard_top_services_ajax",
    "dashboard_income_by_category_ajax",
    "client_export",
    "client_import",
    "client_example_export",
}

PARA_TODO_EL_EQUIPO = {
    "calendar",
    "calendar_list",
    "calendar_appointments",
    "create_appointment_from_calendar",
    "agenda_list",
    "agenda_update_modal",
    "agenda_see_modal",
    "agenda_confirmation_modal",
    "agenda_cancel_modal",
    "agenda_restore_modal",
    "agenda_delete_modal",
    "service_details_ajax",
    "available_hours_ajax",
    "services_by_category_ajax",
    "clients",
    "client_list",
    "client_create_modal",
    "client_detail_modal",
    "client_whatsapp_modal",
    "client_delete_modal",
    "tasks",
    "task_list",
    "task_detail_modal",
    "login",
    "logout",
    "cambiar_clave",
    "profile_modal",
    "session_ping",
}


def administra_el_negocio(usuario):
    if not usuario.is_authenticated or connection.schema_name == get_public_schema_name():
        return False
    try:
        return usuario.perfil.rol in ROLES_QUE_ADMINISTRAN
    except Perfil.DoesNotExist:
        return False
