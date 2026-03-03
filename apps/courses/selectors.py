from django.db.models import QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.courses.models import Course, CourseEnrollment
from apps.users.models import User


def list_courses(*, user: User) -> QuerySet[Course]:
    qs = Course.objects.select_related("teacher")
    if user.role == User.Role.ADMIN:
        return qs.all()
    if user.role == User.Role.TEACHER:
        return qs.filter(teacher=user)
    return qs.none()


def get_course(*, pk: int, user: User) -> Course:
    try:
        course = Course.objects.select_related("teacher").get(pk=pk)
    except Course.DoesNotExist:
        raise NotFound("Course not found.")

    if user.role == User.Role.ADMIN:
        return course
    if user.role == User.Role.TEACHER and course.teacher_id == user.id:
        return course
    raise PermissionDenied("You do not have access to this course.")


def student_ids_for_teacher(*, teacher: User) -> QuerySet[int]:
    return CourseEnrollment.objects.filter(
        course__teacher=teacher,
    ).values_list("student_id", flat=True)
