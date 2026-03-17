import datetime

from hordak.models import Account

from apps.journal.models import JournalEntry


def seed_opening_chart() -> dict[str, Account]:
    root_assets = Account.objects.create(code="1", name="ACTIVO", type="AS", currencies=["ARS"])
    parent_cash = Account.objects.create(
        code=".01",
        name="Caja",
        parent=root_assets,
        type="AS",
        currencies=["ARS"],
    )
    parent_bank = Account.objects.create(
        code=".04",
        name="Bancos",
        parent=root_assets,
        type="AS",
        currencies=["ARS"],
    )
    parent_furniture = Account.objects.create(
        code=".13",
        name="Muebles y Utiles",
        parent=root_assets,
        type="AS",
        currencies=["ARS"],
    )
    root_liabilities = Account.objects.create(
        code="2",
        name="PASIVO",
        type="LI",
        currencies=["ARS"],
    )
    parent_suppliers = Account.objects.create(
        code=".01",
        name="Proveedores",
        parent=root_liabilities,
        type="LI",
        currencies=["ARS"],
    )
    parent_creditors = Account.objects.create(
        code=".02",
        name="Acreedores Varios",
        parent=root_liabilities,
        type="LI",
        currencies=["ARS"],
    )
    root_equity = Account.objects.create(
        code="3",
        name="PATRIMONIO NETO",
        type="EQ",
        currencies=["ARS"],
    )
    parent_capital = Account.objects.create(
        code=".01",
        name="Capital",
        parent=root_equity,
        type="EQ",
        currencies=["ARS"],
    )
    return {
        "cash": parent_cash,
        "bank": parent_bank,
        "furniture": parent_furniture,
        "suppliers": parent_suppliers,
        "creditors": parent_creditors,
        "capital": parent_capital,
    }


def create_legacy_journal_entry(
    *, company, created_by, date: datetime.date | None = None
) -> JournalEntry:
    return JournalEntry.objects.create(
        company=company,
        entry_number=1,
        date=date or datetime.date(2026, 3, 16),
        description="Legacy entry",
        source_type=JournalEntry.SourceType.MANUAL,
        source_ref="LEGACY-001",
        created_by=created_by,
    )
