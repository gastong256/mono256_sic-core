from rest_framework.exceptions import ValidationError

from apps.accounts.visibility import invalidate_student_teacher_cache
from apps.courses.models import Course, CourseEnrollment
from apps.users.models import User


def create_course(*, teacher: User, name: str, code: str | None = None) -> Course:
    if teacher.role != User.Role.TEACHER:
        raise ValidationError({"teacher": "Only teacher users can own courses."})

    course = Course(
        teacher=teacher,
        name=name,
        code=code or None,
    )
    course.full_clean()
    course.save()
    return course


def update_course(*, course: Course, name: str | None = None, code: str | None = None) -> Course:
    if name is not None:
        course.name = name
    if code is not None:
        course.code = code or None

    course.full_clean()
    course.save()
    return course


def delete_course(*, course: Course) -> None:
    course.delete()


def enroll_student(*, course: Course, student: User) -> CourseEnrollment:
    if student.role != User.Role.STUDENT:
        raise ValidationError({"student_id": "Only student users can be enrolled."})

    existing = CourseEnrollment.objects.filter(student=student).first()
    if existing and existing.course_id != course.id:
        raise ValidationError({"student_id": "Student is already enrolled in another course."})
    if existing:
        return existing

    enrollment = CourseEnrollment(course=course, student=student)
    enrollment.full_clean()
    enrollment.save()
    invalidate_student_teacher_cache(student_id=student.id)
    return enrollment


def unenroll_student(*, course: Course, student: User) -> None:
    deleted, _ = CourseEnrollment.objects.filter(course=course, student=student).delete()
    if deleted == 0:
        raise ValidationError({"student_id": "Student is not enrolled in this course."})
    invalidate_student_teacher_cache(student_id=student.id)
