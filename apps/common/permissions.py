from rest_framework.permissions import BasePermission

from apps.users.models import User


class IsAdminRole(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == User.Role.ADMIN
        )


class IsTeacherOrAdminRole(BasePermission):
    message = "Teacher or admin role required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None) in {User.Role.TEACHER, User.Role.ADMIN}
        )


class IsStudentRole(BasePermission):
    message = "Student role required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == User.Role.STUDENT
        )


class IsTeacherStudentOrAdmin(BasePermission):
    message = "Authenticated role required."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and getattr(user, "role", None)
            in {User.Role.TEACHER, User.Role.STUDENT, User.Role.ADMIN}
        )
