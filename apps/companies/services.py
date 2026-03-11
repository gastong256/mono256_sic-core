from django.db.models import ProtectedError

from config.exceptions import ConflictError
from apps.companies.models import Company


def create_company(*, name: str, tax_id: str = "", owner) -> Company:
    company = Company(name=name, tax_id=tax_id, owner=owner)
    company.full_clean()
    company.save()
    return company


def update_company(
    *, company: Company, name: str | None = None, tax_id: str | None = None
) -> Company:
    if name is not None:
        company.name = name
    if tax_id is not None:
        company.tax_id = tax_id
    company.full_clean()
    company.save()
    return company


def delete_company(*, company: Company) -> None:
    try:
        company.delete()
    except ProtectedError:
        raise ConflictError(
            "Cannot delete company with posted journal entries or protected records."
        )
