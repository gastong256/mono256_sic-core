import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from config.exceptions import ConflictError
from apps.closing.models import ClosingSnapshot, ClosingSnapshotLine
from apps.closing.selectors import (
    get_current_logical_exercise,
    list_logical_exercises,
    serialize_logical_exercise,
)
from apps.closing.support import ensure_company_closing_accounts
from apps.companies.opening import assert_company_accounting_ready, company_has_opening_entry
from apps.companies.models import Company
from apps.companies.services import assert_company_writable
from apps.journal import services as journal_services
from apps.journal.models import JournalEntry, JournalEntryLine
from apps.users.models import User

_ZERO = Decimal("0")


@dataclass(frozen=True)
class ClosingRequest:
    closing_date: datetime.date
    reopening_date: datetime.date
    cash_actual: Decimal | None
    inventory_actual: Decimal | None


@dataclass
class BalanceNode:
    key: str
    account_id: int | None
    account_code: str | None
    account_name: str
    parent_code: str
    parent_name: str
    root_code: str
    account_type: str
    total_debit: Decimal = _ZERO
    total_credit: Decimal = _ZERO

    @property
    def debit_balance(self) -> Decimal:
        net = self.total_debit - self.total_credit
        return net if net > _ZERO else _ZERO

    @property
    def credit_balance(self) -> Decimal:
        net = self.total_credit - self.total_debit
        return net if net > _ZERO else _ZERO


def _account_key(*, account_id: int | None, parent_code: str, name: str) -> str:
    if account_id is not None:
        return f"id:{account_id}"
    return f"virtual:{parent_code}|{name.strip().lower()}"


def _draft_line(
    *,
    account_id: int | None,
    account_code: str | None,
    account_name: str,
    parent_code: str,
    line_type: str,
    amount: Decimal,
) -> dict:
    return {
        "account_id": account_id,
        "account_code": account_code,
        "account_name": account_name,
        "parent_code": parent_code,
        "type": line_type,
        "amount": f"{amount:.2f}",
    }


def _draft_entry(
    *,
    date: datetime.date,
    description: str,
    source_type: str,
    source_ref: str,
    lines: list[dict],
) -> dict:
    total_debit = sum(
        (
            Decimal(line["amount"])
            for line in lines
            if line["type"] == JournalEntryLine.LineType.DEBIT
        ),
        start=_ZERO,
    )
    total_credit = sum(
        (
            Decimal(line["amount"])
            for line in lines
            if line["type"] == JournalEntryLine.LineType.CREDIT
        ),
        start=_ZERO,
    )
    return {
        "date": str(date),
        "description": description,
        "source_type": source_type,
        "source_ref": source_ref,
        "lines": lines,
        "total_debit": f"{total_debit:.2f}",
        "total_credit": f"{total_credit:.2f}",
    }


def _build_request(*, data: dict) -> ClosingRequest:
    return ClosingRequest(
        closing_date=data["closing_date"],
        reopening_date=data["reopening_date"],
        cash_actual=data.get("cash_actual"),
        inventory_actual=data.get("inventory_actual"),
    )


def _validate_request(*, company: Company, request: ClosingRequest) -> None:
    assert_company_writable(company=company)
    assert_company_accounting_ready(company=company)
    list_logical_exercises(company=company)
    current_exercise = get_current_logical_exercise(company=company)

    if current_exercise is None or current_exercise.status != "open":
        raise ConflictError("This company does not have an open logical exercise to close.")

    if request.closing_date < current_exercise.start_date:
        raise ConflictError(
            f"The closing date must be on or after the logical exercise start date "
            f"({current_exercise.start_date})."
        )

    if company.books_closed_until and request.closing_date <= company.books_closed_until:
        raise ConflictError(
            f"Books are already closed until {company.books_closed_until}. "
            f"Use a closing date after {company.books_closed_until}."
        )

    if request.reopening_date <= request.closing_date:
        raise ValidationError({"reopening_date": "Reopening date must be after the closing date."})

    if company.journal_entries.filter(date__gt=request.closing_date).exists():
        raise ConflictError(
            "Cannot execute a closing while the company already has later accounting entries."
        )

    if company.journal_entries.filter(
        source_type=JournalEntry.SourceType.PATRIMONIAL_CLOSING,
        date=request.closing_date,
    ).exists():
        raise ConflictError("A patrimonial closing already exists for that closing date.")

    if company.journal_entries.filter(
        source_type=JournalEntry.SourceType.REOPENING,
        date=request.reopening_date,
    ).exists():
        raise ConflictError("A reopening entry already exists for that reopening date.")


def assert_can_manage_company_closing(*, actor, company: Company) -> None:
    if actor.role == User.Role.ADMIN:
        return
    if company.owner_id == actor.id:
        return
    raise PermissionDenied(
        "You do not have permission to execute the accounting closing for this company."
    )


def _load_balance_nodes(*, company: Company, date_to: datetime.date) -> dict[str, BalanceNode]:
    rows = (
        JournalEntryLine.objects.filter(
            journal_entry__company=company,
            journal_entry__date__lte=date_to,
            account__company_account__company=company,
        )
        .values(
            "account_id",
            "account__full_code",
            "account__name",
            "account__type",
            "account__parent__full_code",
            "account__parent__name",
            "account__parent__parent__full_code",
        )
        .annotate(
            total_debit=Sum("amount", filter=Q(type=JournalEntryLine.LineType.DEBIT)),
            total_credit=Sum("amount", filter=Q(type=JournalEntryLine.LineType.CREDIT)),
        )
        .order_by("account__full_code")
    )

    balances: dict[str, BalanceNode] = {}
    for row in rows:
        account_id = int(row["account_id"])
        parent_code = row["account__parent__full_code"]
        name = row["account__name"]
        key = _account_key(account_id=account_id, parent_code=parent_code, name=name)
        balances[key] = BalanceNode(
            key=key,
            account_id=account_id,
            account_code=row["account__full_code"],
            account_name=name,
            parent_code=parent_code,
            parent_name=row["account__parent__name"],
            root_code=row["account__parent__parent__full_code"],
            account_type=row["account__type"],
            total_debit=row["total_debit"] or _ZERO,
            total_credit=row["total_credit"] or _ZERO,
        )
    return balances


def _get_or_create_virtual_balance(
    *,
    balances: dict[str, BalanceNode],
    parent_code: str,
    parent_name: str,
    name: str,
    root_code: str,
    account_type: str,
) -> BalanceNode:
    key = _account_key(account_id=None, parent_code=parent_code, name=name)
    node = balances.get(key)
    if node is None:
        node = BalanceNode(
            key=key,
            account_id=None,
            account_code=None,
            account_name=name,
            parent_code=parent_code,
            parent_name=parent_name,
            root_code=root_code,
            account_type=account_type,
        )
        balances[key] = node
    return node


def _apply_entry_to_balances(*, balances: dict[str, BalanceNode], entry: dict) -> None:
    root_code_by_parent = {
        "1.01": "1",
        "1.09": "1",
        "3.02": "3",
        "4.01": "4",
        "4.12": "4",
        "4.13": "4",
        "5.06": "5",
        "5.07": "5",
    }
    parent_name_by_code = {
        "1.01": "Caja",
        "1.09": "Mercaderías",
        "3.02": "Resultado del Ejercicio",
        "4.01": "Costo de Mercaderías Vendidas",
        "4.12": "Faltante de Caja",
        "4.13": "Faltante de Mercaderías",
        "5.06": "Sobrante de Caja",
        "5.07": "Sobrante de Mercaderías",
    }
    account_type_by_root = {"1": "AS", "2": "LI", "3": "EQ", "4": "EX", "5": "IN"}

    for line in entry["lines"]:
        parent_code = line["parent_code"]
        name = line["account_name"]
        account_id = line["account_id"]
        key = _account_key(account_id=account_id, parent_code=parent_code, name=name)
        node = balances.get(key)
        if node is None:
            root_code = root_code_by_parent.get(parent_code, parent_code.split(".", 1)[0])
            node = _get_or_create_virtual_balance(
                balances=balances,
                parent_code=parent_code,
                parent_name=parent_name_by_code.get(parent_code, parent_code),
                name=name,
                root_code=root_code,
                account_type=account_type_by_root[root_code],
            )
        amount = Decimal(line["amount"])
        if line["type"] == JournalEntryLine.LineType.DEBIT:
            node.total_debit += amount
        else:
            node.total_credit += amount


def _aggregate_parent_balance(
    *, balances: dict[str, BalanceNode], parent_code: str
) -> tuple[Decimal, Decimal, Decimal]:
    debit = sum(
        (node.total_debit for node in balances.values() if node.parent_code == parent_code),
        start=_ZERO,
    )
    credit = sum(
        (node.total_credit for node in balances.values() if node.parent_code == parent_code),
        start=_ZERO,
    )
    return debit, credit, debit - credit


def _validate_patrimonial_natural_balances(*, balances: dict[str, BalanceNode]) -> None:
    grouped: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
    for node in balances.values():
        if node.root_code not in {"1", "2", "3"}:
            continue
        key = (node.root_code, node.parent_code)
        debit, credit = grouped.get(key, (_ZERO, _ZERO))
        grouped[key] = (debit + node.total_debit, credit + node.total_credit)

    invalid_assets = [
        parent_code
        for (root_code, parent_code), (debit, credit) in grouped.items()
        if root_code == "1" and (debit - credit) < _ZERO
    ]
    if invalid_assets:
        raise ConflictError("Asset balances must remain debit-normal before closing.")

    invalid_liabilities = [
        parent_code
        for (root_code, parent_code), (debit, credit) in grouped.items()
        if root_code == "2" and (credit - debit) < _ZERO
    ]
    if invalid_liabilities:
        raise ConflictError("Liability balances must remain credit-normal before closing.")

    invalid_equity = [
        parent_code
        for (root_code, parent_code), (debit, credit) in grouped.items()
        if root_code == "3" and (credit - debit) < _ZERO
    ]
    if invalid_equity:
        raise ConflictError("Equity balances must remain credit-normal before closing.")


def _build_adjustment_entries(
    *,
    request: ClosingRequest,
    balances: dict[str, BalanceNode],
) -> tuple[list[dict], dict]:
    entries: list[dict] = []

    cash_summary = {
        "book_balance": None,
        "actual_balance": None,
        "difference": None,
        "status": "not_requested",
        "entry": None,
    }
    inventory_summary = {
        "book_balance": None,
        "actual_balance": None,
        "difference": None,
        "status": "not_requested",
        "entry": None,
    }

    if request.cash_actual is not None:
        _, _, book_cash = _aggregate_parent_balance(balances=balances, parent_code="1.01")
        difference = request.cash_actual - book_cash
        cash_summary = {
            "book_balance": f"{book_cash:.2f}",
            "actual_balance": f"{request.cash_actual:.2f}",
            "difference": f"{difference:.2f}",
            "status": (
                "balanced"
                if difference == _ZERO
                else ("surplus" if difference > _ZERO else "shortage")
            ),
            "entry": None,
        }
        if difference != _ZERO:
            amount = abs(difference)
            if difference > _ZERO:
                lines = [
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Caja",
                        parent_code="1.01",
                        line_type=JournalEntryLine.LineType.DEBIT,
                        amount=amount,
                    ),
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Sobrante de Caja",
                        parent_code="5.06",
                        line_type=JournalEntryLine.LineType.CREDIT,
                        amount=amount,
                    ),
                ]
            else:
                lines = [
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Faltante de Caja",
                        parent_code="4.12",
                        line_type=JournalEntryLine.LineType.DEBIT,
                        amount=amount,
                    ),
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Caja",
                        parent_code="1.01",
                        line_type=JournalEntryLine.LineType.CREDIT,
                        amount=amount,
                    ),
                ]
            entry = _draft_entry(
                date=request.closing_date,
                description="s/ Arqueo realizado a la fecha",
                source_type=JournalEntry.SourceType.ADJUSTMENT,
                source_ref="CLOSING-CASH",
                lines=lines,
            )
            entries.append(entry)
            cash_summary["entry"] = entry
            _apply_entry_to_balances(balances=balances, entry=entry)

    if request.inventory_actual is not None:
        _, _, book_inventory = _aggregate_parent_balance(balances=balances, parent_code="1.09")
        difference = request.inventory_actual - book_inventory
        inventory_summary = {
            "book_balance": f"{book_inventory:.2f}",
            "actual_balance": f"{request.inventory_actual:.2f}",
            "difference": f"{difference:.2f}",
            "status": (
                "balanced"
                if difference == _ZERO
                else ("surplus" if difference > _ZERO else "shortage")
            ),
            "entry": None,
        }
        if difference != _ZERO:
            amount = abs(difference)
            if difference > _ZERO:
                lines = [
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Mercaderías",
                        parent_code="1.09",
                        line_type=JournalEntryLine.LineType.DEBIT,
                        amount=amount,
                    ),
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Sobrante de Mercaderías",
                        parent_code="5.07",
                        line_type=JournalEntryLine.LineType.CREDIT,
                        amount=amount,
                    ),
                ]
            else:
                lines = [
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Faltante de Mercaderías",
                        parent_code="4.13",
                        line_type=JournalEntryLine.LineType.DEBIT,
                        amount=amount,
                    ),
                    _draft_line(
                        account_id=None,
                        account_code=None,
                        account_name="Mercaderías",
                        parent_code="1.09",
                        line_type=JournalEntryLine.LineType.CREDIT,
                        amount=amount,
                    ),
                ]
            entry = _draft_entry(
                date=request.closing_date,
                description="s/ Inventario de Mercaderías",
                source_type=JournalEntry.SourceType.ADJUSTMENT,
                source_ref="CLOSING-INVENTORY",
                lines=lines,
            )
            entries.append(entry)
            inventory_summary["entry"] = entry
            _apply_entry_to_balances(balances=balances, entry=entry)

    return entries, {"cash": cash_summary, "inventory": inventory_summary}


def _group_statement_nodes(*, nodes: list[BalanceNode], amount_getter) -> list[dict]:
    grouped: dict[str, dict] = {}
    for node in nodes:
        amount = amount_getter(node)
        if amount <= _ZERO:
            continue
        group = grouped.setdefault(
            node.parent_code,
            {
                "account_code": node.parent_code,
                "account_name": node.parent_name,
                "_total": _ZERO,
                "accounts": [],
            },
        )
        group["_total"] += amount
        group["accounts"].append(
            {
                "account_id": node.account_id,
                "account_code": node.account_code,
                "account_name": node.account_name,
                "account_type": node.account_type,
                "amount": f"{amount:.2f}",
            }
        )

    result = []
    for group in sorted(grouped.values(), key=lambda item: item["account_code"]):
        result.append(
            {
                "account_code": group["account_code"],
                "account_name": group["account_name"],
                "subtotal": f"{group['_total']:.2f}",
                "accounts": group["accounts"],
            }
        )
    return result


def _collect_result_nodes(
    *, balances: dict[str, BalanceNode]
) -> tuple[list[BalanceNode], list[BalanceNode], Decimal, Decimal, Decimal]:
    negative_accounts = [
        node for node in balances.values() if node.root_code == "4" and node.debit_balance > _ZERO
    ]
    positive_accounts = [
        node for node in balances.values() if node.root_code == "5" and node.credit_balance > _ZERO
    ]

    invalid_negative = [
        node.account_code or node.account_name
        for node in balances.values()
        if node.root_code == "4" and node.credit_balance > _ZERO
    ]
    if invalid_negative:
        raise ConflictError(
            "Negative result accounts must have debit balances before closing the result."
        )

    invalid_positive = [
        node.account_code or node.account_name
        for node in balances.values()
        if node.root_code == "5" and node.debit_balance > _ZERO
    ]
    if invalid_positive:
        raise ConflictError(
            "Positive result accounts must have credit balances before closing the result."
        )

    total_negative = sum((node.debit_balance for node in negative_accounts), start=_ZERO)
    total_positive = sum((node.credit_balance for node in positive_accounts), start=_ZERO)
    net = total_positive - total_negative
    return negative_accounts, positive_accounts, total_negative, total_positive, net


def _build_income_statement(*, balances: dict[str, BalanceNode]) -> dict:
    negative_accounts, positive_accounts, total_negative, total_positive, net = (
        _collect_result_nodes(balances=balances)
    )
    return {
        "date": None,
        "positive_results": {
            "accounts": _group_statement_nodes(
                nodes=positive_accounts,
                amount_getter=lambda node: node.credit_balance,
            ),
            "total": f"{total_positive:.2f}",
        },
        "negative_results": {
            "accounts": _group_statement_nodes(
                nodes=negative_accounts,
                amount_getter=lambda node: node.debit_balance,
            ),
            "total": f"{total_negative:.2f}",
        },
        "net_result": {
            "amount": f"{net:.2f}",
            "kind": "gain" if net > _ZERO else "loss" if net < _ZERO else "neutral",
        },
    }


def _build_balance_sheet(*, balances: dict[str, BalanceNode], income_statement: dict) -> dict:
    asset_nodes = [
        node for node in balances.values() if node.root_code == "1" and node.debit_balance > _ZERO
    ]
    liability_nodes = [
        node for node in balances.values() if node.root_code == "2" and node.credit_balance > _ZERO
    ]
    equity_nodes = [
        node for node in balances.values() if node.root_code == "3" and node.credit_balance > _ZERO
    ]

    assets_total = sum((node.debit_balance for node in asset_nodes), start=_ZERO)
    liabilities_total = sum((node.credit_balance for node in liability_nodes), start=_ZERO)
    equity_total = sum((node.credit_balance for node in equity_nodes), start=_ZERO)
    net_result = Decimal(income_statement["net_result"]["amount"])
    total_equity = equity_total + net_result

    return {
        "assets": {
            "groups": _group_statement_nodes(
                nodes=asset_nodes,
                amount_getter=lambda node: node.debit_balance,
            ),
            "total": f"{assets_total:.2f}",
        },
        "liabilities": {
            "groups": _group_statement_nodes(
                nodes=liability_nodes,
                amount_getter=lambda node: node.credit_balance,
            ),
            "total": f"{liabilities_total:.2f}",
        },
        "equity": {
            "groups": _group_statement_nodes(
                nodes=equity_nodes,
                amount_getter=lambda node: node.credit_balance,
            ),
            "derived_result": {
                "name": "Resultado del Ejercicio",
                "amount": f"{net_result:.2f}",
                "kind": income_statement["net_result"]["kind"],
            },
            "total": f"{total_equity:.2f}",
        },
        "equation": {
            "total_assets": f"{assets_total:.2f}",
            "total_liabilities_plus_equity": f"{(liabilities_total + total_equity):.2f}",
            "is_balanced": assets_total == liabilities_total + total_equity,
        },
    }


def _build_result_closing_entries(
    *, request: ClosingRequest, balances: dict[str, BalanceNode]
) -> tuple[list[dict], dict]:
    negative_accounts, positive_accounts, total_negative, total_positive, net = (
        _collect_result_nodes(balances=balances)
    )
    summary = {
        "total_negative": f"{total_negative:.2f}",
        "total_positive": f"{total_positive:.2f}",
        "net_result": f"{net:.2f}",
        "net_kind": ("gain" if net > _ZERO else "loss" if net < _ZERO else "neutral"),
    }

    entries: list[dict] = []
    if negative_accounts:
        lines = [
            _draft_line(
                account_id=None,
                account_code=None,
                account_name="Resultado del Ejercicio",
                parent_code="3.02",
                line_type=JournalEntryLine.LineType.DEBIT,
                amount=total_negative,
            )
        ]
        lines += [
            _draft_line(
                account_id=node.account_id,
                account_code=node.account_code,
                account_name=node.account_name,
                parent_code=node.parent_code,
                line_type=JournalEntryLine.LineType.CREDIT,
                amount=node.debit_balance,
            )
            for node in negative_accounts
        ]
        entry = _draft_entry(
            date=request.closing_date,
            description="Por cierre de cuentas de Resultado Negativo (Pérdidas)",
            source_type=JournalEntry.SourceType.RESULT_CLOSING,
            source_ref="CLOSING-RN",
            lines=lines,
        )
        entries.append(entry)
        _apply_entry_to_balances(balances=balances, entry=entry)

    if positive_accounts:
        lines = [
            _draft_line(
                account_id=node.account_id,
                account_code=node.account_code,
                account_name=node.account_name,
                parent_code=node.parent_code,
                line_type=JournalEntryLine.LineType.DEBIT,
                amount=node.credit_balance,
            )
            for node in positive_accounts
        ]
        lines.append(
            _draft_line(
                account_id=None,
                account_code=None,
                account_name="Resultado del Ejercicio",
                parent_code="3.02",
                line_type=JournalEntryLine.LineType.CREDIT,
                amount=total_positive,
            )
        )
        entry = _draft_entry(
            date=request.closing_date,
            description="Por cierre de cuentas de Resultado Positivo (Ganancias)",
            source_type=JournalEntry.SourceType.RESULT_CLOSING,
            source_ref="CLOSING-RP",
            lines=lines,
        )
        entries.append(entry)
        _apply_entry_to_balances(balances=balances, entry=entry)

    return entries, summary


def _build_snapshot_lines(*, balances: dict[str, BalanceNode]) -> list[dict]:
    lines = []
    for node in sorted(
        (
            node
            for node in balances.values()
            if node.root_code in {"1", "2", "3"}
            and (node.debit_balance > _ZERO or node.credit_balance > _ZERO)
        ),
        key=lambda item: item.account_code or item.parent_code,
    ):
        lines.append(
            {
                "account_id": node.account_id,
                "account_code": node.account_code or "",
                "account_name": node.account_name,
                "account_type": node.account_type,
                "root_code": node.root_code,
                "parent_code": node.parent_code,
                "debit_balance": f"{node.debit_balance:.2f}",
                "credit_balance": f"{node.credit_balance:.2f}",
            }
        )
    return lines


def _build_patrimonial_closing_and_reopening(
    *, request: ClosingRequest, balances: dict[str, BalanceNode]
) -> tuple[dict, dict]:
    patrimonial_nodes = [
        node
        for node in balances.values()
        if node.root_code in {"1", "2", "3"}
        and (node.debit_balance > _ZERO or node.credit_balance > _ZERO)
    ]
    if not patrimonial_nodes:
        raise ConflictError("There are no patrimonial balances to close for the selected date.")

    debit_lines = [
        _draft_line(
            account_id=node.account_id,
            account_code=node.account_code,
            account_name=node.account_name,
            parent_code=node.parent_code,
            line_type=JournalEntryLine.LineType.DEBIT,
            amount=node.credit_balance,
        )
        for node in patrimonial_nodes
        if node.credit_balance > _ZERO
    ]
    credit_lines = [
        _draft_line(
            account_id=node.account_id,
            account_code=node.account_code,
            account_name=node.account_name,
            parent_code=node.parent_code,
            line_type=JournalEntryLine.LineType.CREDIT,
            amount=node.debit_balance,
        )
        for node in patrimonial_nodes
        if node.debit_balance > _ZERO
    ]
    closing_entry = _draft_entry(
        date=request.closing_date,
        description="Por cierre de Cuentas Patrimoniales",
        source_type=JournalEntry.SourceType.PATRIMONIAL_CLOSING,
        source_ref="CLOSING-PATRIMONIAL",
        lines=debit_lines + credit_lines,
    )
    reopening_entry = _draft_entry(
        date=request.reopening_date,
        description="Por apertura de Cuentas Patrimoniales",
        source_type=JournalEntry.SourceType.REOPENING,
        source_ref="REOPENING-PATRIMONIAL",
        lines=[
            _draft_line(
                account_id=line["account_id"],
                account_code=line["account_code"],
                account_name=line["account_name"],
                parent_code=line["parent_code"],
                line_type=(
                    JournalEntryLine.LineType.CREDIT
                    if line["type"] == JournalEntryLine.LineType.DEBIT
                    else JournalEntryLine.LineType.DEBIT
                ),
                amount=Decimal(line["amount"]),
            )
            for line in closing_entry["lines"]
        ],
    )
    return closing_entry, reopening_entry


def build_simplified_closing_plan(*, company: Company, data: dict) -> dict:
    request = _build_request(data=data)
    _validate_request(company=company, request=request)
    current_exercise = get_current_logical_exercise(company=company)
    previous_exercises = [
        serialize_logical_exercise(exercise)
        for exercise in reversed(list_logical_exercises(company=company))
        if current_exercise is None or exercise.exercise_id != current_exercise.exercise_id
    ]

    balances = _load_balance_nodes(company=company, date_to=request.closing_date)
    adjustment_entries, adjustment_summary = _build_adjustment_entries(
        request=request,
        balances=balances,
    )
    _validate_patrimonial_natural_balances(balances=balances)
    income_statement = _build_income_statement(balances=balances)
    income_statement["date"] = str(request.closing_date)
    balance_sheet = _build_balance_sheet(
        balances=balances,
        income_statement=income_statement,
    )
    balance_sheet["date"] = str(request.closing_date)
    result_entries, result_summary = _build_result_closing_entries(
        request=request,
        balances=balances,
    )
    snapshot_lines = _build_snapshot_lines(balances=balances)
    patrimonial_closing_entry, reopening_entry = _build_patrimonial_closing_and_reopening(
        request=request,
        balances=balances,
    )

    return {
        "company_id": company.id,
        "company": company.name,
        "closing_date": str(request.closing_date),
        "reopening_date": str(request.reopening_date),
        "books_closed_until": (
            str(company.books_closed_until) if company.books_closed_until else None
        ),
        "active_exercise": (
            serialize_logical_exercise(current_exercise) if current_exercise is not None else {}
        ),
        "previous_exercises": previous_exercises,
        "adjustments": adjustment_summary,
        "result_summary": result_summary,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "entries": {
            "adjustments": adjustment_entries,
            "result_closing": result_entries,
            "patrimonial_closing": patrimonial_closing_entry,
            "reopening": reopening_entry,
        },
        "_snapshot_lines": snapshot_lines,
    }


def _resolve_line_account_ids(*, company: Company, lines: list[dict]) -> list[dict]:
    support_accounts = ensure_company_closing_accounts(company=company)
    resolved_lines: list[dict] = []
    for line in lines:
        account_id = line["account_id"]
        if account_id is None:
            key = (line["parent_code"], line["account_name"].strip().lower())
            try:
                account = support_accounts[key]
            except KeyError as exc:
                raise ConflictError(
                    f"Support account '{line['account_name']}' under '{line['parent_code']}' is unavailable."
                ) from exc
            account_id = account.id
        resolved_lines.append(
            {
                "account_id": account_id,
                "type": line["type"],
                "amount": Decimal(line["amount"]),
            }
        )
    return resolved_lines


def _create_snapshot(
    *,
    company: Company,
    patrimonial_closing_entry: JournalEntry,
    reopening_entry: JournalEntry,
    balance_sheet: dict,
    income_statement: dict,
    snapshot_lines: list[dict],
) -> ClosingSnapshot:
    snapshot = ClosingSnapshot.objects.create(
        company=company,
        patrimonial_closing_entry=patrimonial_closing_entry,
        reopening_entry=reopening_entry,
        closing_date=patrimonial_closing_entry.date,
        reopening_date=reopening_entry.date,
        balance_sheet_payload=balance_sheet,
        income_statement_payload=income_statement,
    )
    ClosingSnapshotLine.objects.bulk_create(
        [
            ClosingSnapshotLine(
                snapshot=snapshot,
                account_id=line["account_id"],
                account_code=line["account_code"],
                account_name=line["account_name"],
                account_type=line["account_type"],
                root_code=line["root_code"],
                parent_code=line["parent_code"],
                debit_balance=Decimal(line["debit_balance"]),
                credit_balance=Decimal(line["credit_balance"]),
            )
            for line in snapshot_lines
        ]
    )
    return snapshot


@transaction.atomic
def execute_simplified_closing(*, company: Company, actor, data: dict) -> dict:
    assert_can_manage_company_closing(actor=actor, company=company)
    plan = build_simplified_closing_plan(company=company, data=data)

    created_entries: list[JournalEntry] = []
    patrimonial_closing_entry: JournalEntry | None = None
    reopening_entry: JournalEntry | None = None
    ordered_entries = (
        plan["entries"]["adjustments"]
        + plan["entries"]["result_closing"]
        + [plan["entries"]["patrimonial_closing"], plan["entries"]["reopening"]]
    )

    for draft_entry in ordered_entries:
        entry = journal_services.create_journal_entry(
            company=company,
            created_by=actor,
            date=datetime.date.fromisoformat(draft_entry["date"]),
            description=draft_entry["description"],
            source_type=draft_entry["source_type"],
            source_ref=draft_entry["source_ref"],
            lines=_resolve_line_account_ids(company=company, lines=draft_entry["lines"]),
        )
        created_entries.append(entry)
        if entry.source_type == JournalEntry.SourceType.PATRIMONIAL_CLOSING:
            patrimonial_closing_entry = entry
        elif entry.source_type == JournalEntry.SourceType.REOPENING:
            reopening_entry = entry

    if patrimonial_closing_entry is None or reopening_entry is None:
        raise ConflictError("The simplified closing did not generate the required closing entries.")

    snapshot = _create_snapshot(
        company=company,
        patrimonial_closing_entry=patrimonial_closing_entry,
        reopening_entry=reopening_entry,
        balance_sheet=plan["balance_sheet"],
        income_statement=plan["income_statement"],
        snapshot_lines=plan["_snapshot_lines"],
    )

    company.books_closed_until = datetime.date.fromisoformat(plan["closing_date"])
    company.full_clean()
    company.save(update_fields=["books_closed_until", "updated_at"])

    return {
        "company_id": company.id,
        "company": company.name,
        "closing_date": plan["closing_date"],
        "reopening_date": plan["reopening_date"],
        "books_closed_until": plan["closing_date"],
        "snapshot_id": snapshot.id,
        "created_entries": [
            {
                "id": entry.id,
                "entry_number": entry.entry_number,
                "date": str(entry.date),
                "description": entry.description,
                "source_type": entry.source_type,
                "source_ref": entry.source_ref,
            }
            for entry in created_entries
        ],
    }


def get_closing_state(*, company: Company) -> dict:
    last_patrimonial = (
        company.journal_entries.filter(source_type=JournalEntry.SourceType.PATRIMONIAL_CLOSING)
        .order_by("-date", "-entry_number")
        .first()
    )
    last_reopening = (
        company.journal_entries.filter(source_type=JournalEntry.SourceType.REOPENING)
        .order_by("-date", "-entry_number")
        .first()
    )
    current_exercise = get_current_logical_exercise(company=company)
    return {
        "company_id": company.id,
        "company": company.name,
        "books_closed_until": (
            str(company.books_closed_until) if company.books_closed_until else None
        ),
        "last_patrimonial_closing_entry_id": last_patrimonial.id if last_patrimonial else None,
        "last_patrimonial_closing_date": str(last_patrimonial.date) if last_patrimonial else None,
        "last_reopening_entry_id": last_reopening.id if last_reopening else None,
        "last_reopening_date": str(last_reopening.date) if last_reopening else None,
        "current_exercise": (
            serialize_logical_exercise(current_exercise) if current_exercise is not None else None
        ),
        "can_close": bool(
            current_exercise
            and current_exercise.status == "open"
            and company_has_opening_entry(company=company)
            and not company.is_read_only
        ),
    }


def serialize_snapshot(*, snapshot: ClosingSnapshot) -> dict:
    return {
        "id": snapshot.id,
        "company_id": snapshot.company_id,
        "company": snapshot.company.name,
        "patrimonial_closing_entry_id": snapshot.patrimonial_closing_entry_id,
        "reopening_entry_id": snapshot.reopening_entry_id,
        "closing_date": str(snapshot.closing_date),
        "reopening_date": str(snapshot.reopening_date),
        "balance_sheet": snapshot.balance_sheet_payload,
        "income_statement": snapshot.income_statement_payload,
        "lines": [
            {
                "account_id": line.account_id,
                "account_code": line.account_code,
                "account_name": line.account_name,
                "account_type": line.account_type,
                "root_code": line.root_code,
                "parent_code": line.parent_code,
                "debit_balance": f"{line.debit_balance:.2f}",
                "credit_balance": f"{line.credit_balance:.2f}",
            }
            for line in snapshot.lines.all()
        ],
    }
