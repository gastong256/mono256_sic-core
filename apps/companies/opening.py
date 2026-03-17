import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from django.db.models import Exists, OuterRef, QuerySet, Subquery
from rest_framework.exceptions import PermissionDenied, ValidationError

from config.exceptions import ConflictError
from apps.companies.models import Company
from apps.journal.models import JournalEntry
from apps.users.models import User

OPENING_ASSET_PARENT_CODES = frozenset(
    {
        "1.01",  # Caja
        "1.02",  # Valores a Depositar
        "1.04",  # Bancos
        "1.06",  # Deudores por Ventas
        "1.08",  # Documentos a Cobrar
        "1.09",  # Mercaderías
        "1.11",  # Inmuebles
        "1.12",  # Rodados
        "1.13",  # Muebles y Útiles
        "1.14",  # Instalaciones
        "1.15",  # Maquinarias
        "1.16",  # Equipos de Computación
    }
)
OPENING_LIABILITY_PARENT_CODES = frozenset(
    {
        "2.01",  # Proveedores
        "2.02",  # Acreedores Varios
        "2.03",  # Documentos a Pagar
    }
)
OPENING_CAPITAL_PARENT_CODE = "3.01"

OPENING_DESCRIPTION_BY_KIND = {
    "INITIAL": "s/ Inventario Inicial",
    "GENERAL": "s/ Inventario General",
}


@dataclass(frozen=True)
class OpeningAccountSpec:
    parent_code: str
    name: str
    amount: Decimal


@dataclass(frozen=True)
class OpeningEntryPayload:
    date: datetime.date
    inventory_kind: str
    source_ref: str
    assets: tuple[OpeningAccountSpec, ...]
    liabilities: tuple[OpeningAccountSpec, ...]


def _coerce_opening_specs(
    *, items: Sequence[Mapping[str, object]]
) -> tuple[OpeningAccountSpec, ...]:
    return tuple(
        OpeningAccountSpec(
            parent_code=str(item["parent_code"]),
            name=str(item["name"]).strip(),
            amount=Decimal(str(item["amount"])),
        )
        for item in items
    )


def build_opening_entry_payload(*, data: Mapping[str, object]) -> OpeningEntryPayload:
    raw_assets = data.get("assets", [])
    raw_liabilities = data.get("liabilities", [])

    if not isinstance(raw_assets, Sequence) or isinstance(raw_assets, (str, bytes)):
        raise ValidationError({"opening_entry": "Assets payload must be a list."})
    if not isinstance(raw_liabilities, Sequence) or isinstance(raw_liabilities, (str, bytes)):
        raise ValidationError({"opening_entry": "Liabilities payload must be a list."})

    raw_date = data["date"]
    if isinstance(raw_date, str):
        try:
            opening_date = datetime.date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValidationError({"opening_entry": "Opening date is invalid."}) from exc
    elif isinstance(raw_date, datetime.date):
        opening_date = raw_date
    else:
        raise ValidationError({"opening_entry": "Opening date is invalid."})

    return OpeningEntryPayload(
        date=opening_date,
        inventory_kind=str(data.get("inventory_kind", "INITIAL")),
        source_ref=str(data.get("source_ref", "")),
        assets=_coerce_opening_specs(items=raw_assets),
        liabilities=_coerce_opening_specs(items=raw_liabilities),
    )


def with_accounting_state(queryset: QuerySet[Company]) -> QuerySet[Company]:
    opening_exists = JournalEntry.objects.filter(
        company_id=OuterRef("pk"),
        source_type=JournalEntry.SourceType.OPENING,
    )
    opening_ids = opening_exists.values("id")[:1]
    return queryset.annotate(
        has_opening_entry=Exists(opening_exists),
        opening_entry_id=Subquery(opening_ids),
    )


def company_has_opening_entry(*, company: Company) -> bool:
    if hasattr(company, "has_opening_entry"):
        return bool(company.has_opening_entry)
    return JournalEntry.objects.filter(
        company=company,
        source_type=JournalEntry.SourceType.OPENING,
    ).exists()


def assert_company_accounting_ready(*, company: Company) -> None:
    if not company_has_opening_entry(company=company):
        raise ConflictError(
            "This company must be opened with an inventory entry before accounting "
            "operations or reports are available."
        )


def assert_can_manage_company_opening(*, actor, company: Company) -> None:
    if actor.role == User.Role.ADMIN:
        return
    if company.owner_id == actor.id:
        return
    raise PermissionDenied(
        "You do not have permission to create the opening entry for this company."
    )


def opening_description_for_kind(*, inventory_kind: str) -> str:
    try:
        return OPENING_DESCRIPTION_BY_KIND[inventory_kind]
    except KeyError as exc:
        raise ValidationError({"inventory_kind": "Invalid inventory kind."}) from exc
