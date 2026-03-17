from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.users.models import User


def resolve_teacher_for_actor(
    *,
    actor: User,
    teacher_id: int | None,
    missing_teacher_id_message: str,
) -> User:
    if actor.role == User.Role.TEACHER:
        return actor

    if actor.role == User.Role.ADMIN:
        if not teacher_id:
            raise ValidationError({"teacher_id": missing_teacher_id_message})
        teacher = User.objects.filter(pk=teacher_id).first()
        if teacher is None:
            raise ValidationError({"teacher_id": "Teacher not found."})
        if teacher.role != User.Role.TEACHER:
            raise ValidationError({"teacher_id": "Selected user is not a teacher."})
        return teacher

    raise PermissionDenied("Teacher or admin role required.")
