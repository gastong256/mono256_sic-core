from django.db.models import QuerySet
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.companies.models import Company


def list_companies(*, user) -> QuerySet[Company]:
    """
    Return companies visible to the given user.

    Teachers (is_staff=True) see all companies.
    Students see only their own companies.
    """
    if user.is_staff:
        return Company.objects.select_related("owner").all()
    return Company.objects.select_related("owner").filter(owner=user)


def get_company(*, pk: int, user) -> Company:
    """
    Return the company with the given pk, enforcing ownership rules.

    Raises NotFound if the company does not exist.
    Raises PermissionDenied if the user is a student who does not own it.
    """
    try:
        company = Company.objects.select_related("owner").get(pk=pk)
    except Company.DoesNotExist:
        raise NotFound(detail="Company not found.")

    if not user.is_staff and company.owner != user:
        raise PermissionDenied(detail="You do not have permission to access this company.")

    return company
