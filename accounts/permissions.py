from rest_framework.permissions import BasePermission


class IsDispatcher(BasePermission):
    message = "Only dispatchers can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'dispatcher'
        )


class IsDriver(BasePermission):
    message = "Only drivers can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'driver'
        )


class IsDispatcherOrReadOnly(BasePermission):
    """
    Drivers can read; only dispatchers can write.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'dispatcher'