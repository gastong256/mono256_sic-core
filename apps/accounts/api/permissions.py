from rest_framework.permissions import BasePermission


class IsAuthenticatedForAccounts(BasePermission):
    message = "Authentication credentials were not provided."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)
