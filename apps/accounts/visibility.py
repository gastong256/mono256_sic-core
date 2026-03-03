from apps.accounts.models import TeacherAccountVisibility
from apps.users.models import User


def resolve_teacher_for_student(*, student: User) -> User | None:
    from apps.courses.models import CourseEnrollment

    try:
        enrollment = CourseEnrollment.objects.select_related("course__teacher").get(student=student)
    except CourseEnrollment.DoesNotExist:
        return None
    return enrollment.course.teacher


def hidden_account_ids_for_student(*, student: User) -> set[int]:
    teacher = resolve_teacher_for_student(student=student)
    if teacher is None:
        return set()

    return set(
        TeacherAccountVisibility.objects.filter(
            teacher=teacher,
            is_visible=False,
        ).values_list("account_id", flat=True)
    )


def is_hidden_for_student(*, student: User, account_id: int) -> bool:
    return account_id in hidden_account_ids_for_student(student=student)
