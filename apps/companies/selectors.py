from django.db.models import Count, Q, QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.companies.models import Company
from apps.users.models import User


def list_companies(*, user) -> QuerySet[Company]:
    base_qs = Company.objects.select_related("owner").annotate(account_count=Count("accounts"))

    if user.role == User.Role.ADMIN:
        return base_qs.all()

    if user.role == User.Role.TEACHER:
        from apps.courses.selectors import student_ids_for_teacher

        enrolled_ids = student_ids_for_teacher(teacher=user)
        return base_qs.filter(
            Q(owner=user) | Q(owner_id__in=enrolled_ids)
        )

    return base_qs.filter(owner=user)


def get_company(*, pk: int, user) -> Company:
    try:
        company = Company.objects.select_related("owner").get(pk=pk)
    except Company.DoesNotExist:
        raise NotFound(detail="Company not found.")

    if user.role == User.Role.ADMIN:
        return company

    if user.role == User.Role.STUDENT and company.owner_id != user.id:
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
