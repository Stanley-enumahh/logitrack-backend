from rest_framework.permissions import BasePermission


class IsAssignedDriverOrDispatcher(BasePermission):
    """
    Dispatchers can act on any order. Drivers can only act on
    orders assigned to them.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'dispatcher':
            return True
        if request.user.role == 'driver':
            return obj.assigned_driver_id == request.user.id
        return False