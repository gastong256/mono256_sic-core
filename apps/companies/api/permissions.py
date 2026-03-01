from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    """Grants access only to staff users (teachers)."""

    message = "Only teachers can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsCompanyOwner(BasePermission):
    """
    Object-level permission: grants access to the owner of a Company.

    Must be used together with IsAuthenticated (or similar view-level check).
    """

    message = "You do not own this company."

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.owner == request.user


class IsTeacherOrOwner(BasePermission):
    """
    Grants access to teachers or to the owner of the target Company.

    View-level: user must be authenticated.
    Object-level: user is staff OR is the company owner.
    """

    message = "You do not have permission to access this company."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_staff:
            return True
        return obj.owner == request.user
