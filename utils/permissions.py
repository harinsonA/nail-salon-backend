from rest_framework.permissions import BasePermission


class IsAdminOrStaff(BasePermission):
    """
    Permiso personalizado que solo permite acceso a usuarios admin o staff.
    """

    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


class IsOwnerOrAdmin(BasePermission):
    """
    Permiso personalizado que permite acceso al propietario del objeto o admin.
    """

    def has_object_permission(self, request, view, obj):
        # Admin tiene acceso completo
        if request.user.is_staff or request.user.is_superuser:
            return True

        # El propietario puede acceder a su propio objeto
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False
