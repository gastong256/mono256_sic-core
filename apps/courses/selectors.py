from collections import defaultdict

from django.db.models import Count, Max, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.companies.models import Company
from apps.courses.models import Course, CourseDemoCompanyVisibility, CourseEnrollment
from apps.journal.models import JournalEntry
from apps.users.models import User


def list_courses(*, user: User) -> QuerySet[Course]:
    qs = Course.objects.select_related("teacher").annotate(student_count=Count("enrollments"))
    if user.role == User.Role.ADMIN:
        return qs.all()
    if user.role == User.Role.TEACHER:
        return qs.filter(teacher=user)
    return qs.none()


def get_course(*, pk: int, user: User) -> Course:
    try:
        course = (
            Course.objects.select_related("teacher")
            .annotate(student_count=Count("enrollments"))
            .get(pk=pk)
        )
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


def list_course_overviews(*, user: User) -> list[dict]:
    courses = list(list_courses(user=user).order_by("name"))
    if not courses:
        return []

    course_ids = [course.id for course in courses]
    enrollments = list(
        CourseEnrollment.objects.filter(course_id__in=course_ids)
        .select_related("student", "course", "course__teacher")
        .order_by("course__name", "student__username")
    )
    if not enrollments:
        return [
            {
                "course_id": course.id,
                "course_name": course.name,
                "course_code": course.code,
                "teacher_id": course.teacher_id,
                "teacher_username": course.teacher.username,
                "student_count": int(getattr(course, "student_count", 0)),
                "totals": {
                    "company_count": 0,
                    "journal_entry_count": 0,
                },
                "students": [],
            }
            for course in courses
        ]

    student_ids = [enrollment.student_id for enrollment in enrollments]
    company_counts = {
        row["owner_id"]: int(row["company_count"])
        for row in Company.objects.filter(owner_id__in=student_ids)
        .values("owner_id")
        .annotate(company_count=Count("id"))
    }
    journal_counts = {
        row["company__owner_id"]: int(row["journal_entry_count"])
        for row in JournalEntry.objects.filter(company__owner_id__in=student_ids)
        .values("company__owner_id")
        .annotate(journal_entry_count=Count("id"))
    }

    students_by_course: dict[int, list[dict]] = defaultdict(list)
    for enrollment in enrollments:
        company_count = company_counts.get(enrollment.student_id, 0)
        journal_entry_count = journal_counts.get(enrollment.student_id, 0)
        students_by_course[enrollment.course_id].append(
            {
                "student_id": enrollment.student_id,
                "student_username": enrollment.student.username,
                "student_full_name": enrollment.student.get_full_name(),
                "company_count": company_count,
                "journal_entry_count": journal_entry_count,
            }
        )

    overviews: list[dict] = []
    for course in courses:
        students = students_by_course.get(course.id, [])
        overviews.append(
            {
                "course_id": course.id,
                "course_name": course.name,
                "course_code": course.code,
                "teacher_id": course.teacher_id,
                "teacher_username": course.teacher.username,
                "student_count": int(getattr(course, "student_count", len(students))),
                "totals": {
                    "company_count": sum(student["company_count"] for student in students),
                    "journal_entry_count": sum(
                        student["journal_entry_count"] for student in students
                    ),
                },
                "students": students,
            }
        )
    return overviews


def get_teacher_student_context(*, user: User, student_id: int) -> dict:
    try:
        enrollment = CourseEnrollment.objects.select_related(
            "student", "course", "course__teacher"
        ).get(student_id=student_id)
    except CourseEnrollment.DoesNotExist:
        raise NotFound("Student not found.")

    # Reuse course-level permission checks for teacher/admin access.
    get_course(pk=enrollment.course_id, user=user)

    companies = list(
        Company.objects.filter(owner_id=student_id)
        .select_related("owner")
        .annotate(
            account_count=Count("accounts", distinct=True),
            journal_entry_count=Count("journal_entries", distinct=True),
            last_entry_date=Max("journal_entries__date"),
        )
        .order_by("name")
    )
    return {
        "student": {
            "id": enrollment.student_id,
            "username": enrollment.student.username,
            "first_name": enrollment.student.first_name,
            "last_name": enrollment.student.last_name,
            "full_name": enrollment.student.get_full_name(),
            "course_id": enrollment.course_id,
            "course_name": enrollment.course.name,
        },
        "companies": [
            {
                "id": company.id,
                "name": company.name,
                "tax_id": company.tax_id,
                "account_count": int(getattr(company, "account_count", 0)),
                "journal_entry_count": int(getattr(company, "journal_entry_count", 0)),
                "last_entry_date": getattr(company, "last_entry_date", None),
                "books_closed_until": company.books_closed_until,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
            }
            for company in companies
        ],
    }


def list_course_demo_companies(*, course: Course) -> list[dict]:
    demo_companies = list(
        Company.objects.filter(is_demo=True)
        .select_related("owner")
        .annotate(
            account_count=Count("accounts", distinct=True),
            journal_entry_count=Count("journal_entries", distinct=True),
        )
        .order_by("name")
    )
    visibility_by_company_id = {
        row["company_id"]: row["is_visible"]
        for row in CourseDemoCompanyVisibility.objects.filter(course=course).values(
            "company_id",
            "is_visible",
        )
    }

    return [
        {
            "company_id": company.id,
            "company_name": company.name,
            "is_demo": company.is_demo,
            "is_read_only": company.is_read_only,
            "is_visible": bool(visibility_by_company_id.get(company.id, False)),
            "account_count": int(getattr(company, "account_count", 0)),
            "journal_entry_count": int(getattr(company, "journal_entry_count", 0)),
        }
        for company in demo_companies
    ]
