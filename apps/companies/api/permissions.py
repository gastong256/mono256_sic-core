from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsTeacher(BasePermission):
    """Grants access only to teacher/admin role users."""

    message = "Only teachers can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {User.Role.TEACHER, User.Role.ADMIN}
        )


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
        if request.user.role in {User.Role.TEACHER, User.Role.ADMIN}:
            return True
        return obj.owner == request.user
