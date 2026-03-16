from django.db.models import ProtectedError

from config.exceptions import ConflictError
from apps.companies.models import Company


def assert_company_writable(*, company: Company) -> None:
    if company.is_read_only:
        raise ConflictError("This is a read-only demo company.")


def create_company(*, name: str, tax_id: str = "", owner) -> Company:
    company = Company(name=name, tax_id=tax_id, owner=owner)
    company.full_clean()
    company.save()
    return company


def update_company(
    *, company: Company, name: str | None = None, tax_id: str | None = None
) -> Company:
    assert_company_writable(company=company)
    if name is not None:
        company.name = name
    if tax_id is not None:
        company.tax_id = tax_id
    company.full_clean()
    company.save()
    return company


def delete_company(*, company: Company) -> None:
    assert_company_writable(company=company)
    try:
        company.delete()
    except ProtectedError:
        raise ConflictError(
            "Cannot delete company with posted journal entries or protected records."
        )
