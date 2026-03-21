from django.db.models import Count, Q, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.companies.opening import with_accounting_state
from apps.companies.models import Company
from apps.users.models import User


def _visible_demo_company_ids_for_student(*, student: User) -> list[int]:
    from apps.courses.models import CourseDemoCompanyVisibility, CourseEnrollment

    course_id = (
        CourseEnrollment.objects.filter(student=student).values_list("course_id", flat=True).first()
    )
    if course_id is None:
        return []

    return list(
        CourseDemoCompanyVisibility.objects.filter(
            course_id=course_id,
            company__is_demo=True,
            is_visible=True,
        ).values_list("company_id", flat=True)
    )


def _visible_shared_company_ids_for_student(*, student: User) -> list[int]:
    from apps.courses.models import CourseEnrollment, CourseSharedCompanyVisibility

    course_id = (
        CourseEnrollment.objects.filter(student=student).values_list("course_id", flat=True).first()
    )
    if course_id is None:
        return []

    return list(
        CourseSharedCompanyVisibility.objects.filter(
            course_id=course_id,
            company__is_demo=False,
            is_visible=True,
        ).values_list("company_id", flat=True)
    )


def _student_can_access_demo_company(*, student: User, company: Company) -> bool:
    return company.id in _visible_demo_company_ids_for_student(student=student)


def _student_can_access_shared_company(*, student: User, company: Company) -> bool:
    return company.id in _visible_shared_company_ids_for_student(student=student)


def list_companies(*, user) -> QuerySet[Company]:
    base_qs = with_accounting_state(
        Company.objects.select_related("owner").annotate(account_count=Count("accounts"))
    )

    if user.role == User.Role.ADMIN:
        return base_qs.all()

    if user.role == User.Role.TEACHER:
        from apps.courses.selectors import student_ids_for_teacher

        enrolled_ids = student_ids_for_teacher(teacher=user)
        return base_qs.filter(
            Q(is_demo=True, is_published=True) | Q(owner=user) | Q(owner_id__in=enrolled_ids)
        )

    demo_ids = _visible_demo_company_ids_for_student(student=user)
    shared_ids = _visible_shared_company_ids_for_student(student=user)
    student_filter = Q(owner=user, is_demo=False)
    if demo_ids:
        student_filter |= Q(is_demo=True, is_published=True, id__in=demo_ids)
    if shared_ids:
        student_filter |= Q(is_demo=False, id__in=shared_ids)
    return base_qs.filter(student_filter)


def get_company(*, pk: int, user) -> Company:
    try:
        company = with_accounting_state(Company.objects.select_related("owner")).get(pk=pk)
    except Company.DoesNotExist:
        raise NotFound(detail="Company not found.")

    if user.role == User.Role.ADMIN:
        return company

    if company.is_demo:
        if user.role == User.Role.TEACHER:
            if company.is_published:
                return company
            raise PermissionDenied(detail="You do not have permission to access this company.")
        if (
            user.role == User.Role.STUDENT
            and _student_can_access_demo_company(
                student=user,
                company=company,
            )
            and company.is_published
        ):
            return company
        raise PermissionDenied(detail="You do not have permission to access this company.")

    if user.role == User.Role.STUDENT and company.owner_id != user.id:
        if _student_can_access_shared_company(student=user, company=company):
            return company
        raise PermissionDenied(detail="You do not have permission to access this company.")

    if user.role == User.Role.TEACHER:
        if company.owner_id == user.id:
            return company
        from apps.courses.models import CourseEnrollment

        enrolled = CourseEnrollment.objects.filter(
            course__teacher=user,
            student_id=company.owner_id,
        ).exists()
        if enrolled:
            return company
        raise PermissionDenied(detail="You do not have permission to access this company.")

    return company
