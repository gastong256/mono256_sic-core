from rest_framework.permissions import BasePermission


class IsAuthenticatedForAccounts(BasePermission):
    """
    Grants access only to authenticated users.

    Company-level access control (owner vs. teacher) is enforced
    inside the views via the company selectors.
    """

    message = "Authentication credentials were not provided."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)
