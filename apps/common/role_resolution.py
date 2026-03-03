from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.users.models import User


def resolve_teacher_for_actor(
    *,
    actor: User,
    teacher_id: int | None,
    missing_teacher_id_message: str,
) -> User:
    """
    Resolve the teacher target for teacher/admin requests.

    - Teacher actors always resolve to themselves.
    - Admin actors must provide teacher_id.
    - Other roles are rejected.
    """
    if actor.role == User.Role.TEACHER:
        return actor

    if actor.role == User.Role.ADMIN:
        if not teacher_id:
            raise ValidationError({"teacher_id": missing_teacher_id_message})
        try:
            teacher = User.objects.get(pk=teacher_id)
        except User.DoesNotExist as exc:
            raise ValidationError({"teacher_id": "Teacher not found."}) from exc
        if teacher.role != User.Role.TEACHER:
            raise ValidationError({"teacher_id": "Selected user is not a teacher."})
        return teacher

    raise PermissionDenied("Teacher or admin role required.")
