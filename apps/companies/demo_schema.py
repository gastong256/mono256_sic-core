from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from rest_framework.exceptions import ValidationError

from apps.companies.opening import build_opening_entry_payload


@dataclass(frozen=True)
class DemoJournalLine:
    parent_code: str
    name: str
    type: str
    amount: Decimal


@dataclass(frozen=True)
class DemoJournalEntry:
    date: datetime.date
    description: str
    source_type: str
    source_ref: str
    lines: tuple[DemoJournalLine, ...]


@dataclass(frozen=True)
class DemoClosing:
    closing_date: datetime.date
    reopening_date: datetime.date
    cash_actual: Decimal | None
    inventory_actual: Decimal | None


@dataclass(frozen=True)
class DemoLogicalExercise:
    journal_entries: tuple[DemoJournalEntry, ...]
    closing: DemoClosing | None


@dataclass(frozen=True)
class DemoPayload:
    name: str
    description: str
    tax_id: str
    is_published: bool
    opening_entry: dict[str, Any]
    logical_exercises: tuple[DemoLogicalExercise, ...]


def _coerce_str(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValidationError({"demo": f"'{field}' must be a string."})
    return value


def _coerce_bool(value: Any, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError({"demo": f"'{field}' must be a boolean."})
    return value


def _coerce_date(value: Any, *, field: str) -> datetime.date:
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError({"demo": f"'{field}' must be a valid ISO date."}) from exc
    raise ValidationError({"demo": f"'{field}' must be a valid ISO date."})


def _coerce_decimal(value: Any, *, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ValidationError({"demo": f"'{field}' must be a valid decimal."}) from exc


def _assert_exact_keys(*, data: dict[str, Any], allowed: set[str], context: str) -> None:
    extra = set(data.keys()) - allowed
    if extra:
        names = ", ".join(sorted(extra))
        raise ValidationError({"demo": f"{context} contains unsupported keys: {names}."})


def _parse_journal_line(
    raw_line: dict[str, Any], *, index: int, entry_index: int, exercise_index: int
) -> DemoJournalLine:
    if not isinstance(raw_line, dict):
        raise ValidationError(
            {
                "demo": (
                    f"logical_exercises[{exercise_index}].journal_entries[{entry_index}]."
                    f"lines[{index}] must be an object."
                )
            }
        )
    _assert_exact_keys(
        data=raw_line,
        allowed={"parent_code", "name", "type", "amount"},
        context=(
            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}].lines[{index}]"
        ),
    )
    return DemoJournalLine(
        parent_code=_coerce_str(raw_line["parent_code"], field="parent_code").strip(),
        name=_coerce_str(raw_line["name"], field="name").strip(),
        type=_coerce_str(raw_line["type"], field="type").strip(),
        amount=_coerce_decimal(raw_line["amount"], field="amount"),
    )


def _parse_journal_entry(
    raw_entry: dict[str, Any], *, index: int, exercise_index: int
) -> DemoJournalEntry:
    if not isinstance(raw_entry, dict):
        raise ValidationError(
            {
                "demo": f"logical_exercises[{exercise_index}].journal_entries[{index}] must be an object."
            }
        )
    _assert_exact_keys(
        data=raw_entry,
        allowed={"date", "description", "source_type", "source_ref", "lines"},
        context=f"logical_exercises[{exercise_index}].journal_entries[{index}]",
    )
    raw_lines = raw_entry.get("lines")
    if not isinstance(raw_lines, list):
        raise ValidationError(
            {
                "demo": (
                    f"logical_exercises[{exercise_index}].journal_entries[{index}].lines "
                    "must be a list."
                )
            }
        )
    return DemoJournalEntry(
        date=_coerce_date(raw_entry["date"], field="date"),
        description=_coerce_str(raw_entry["description"], field="description").strip(),
        source_type=_coerce_str(raw_entry["source_type"], field="source_type").strip(),
        source_ref=_coerce_str(raw_entry.get("source_ref", ""), field="source_ref").strip(),
        lines=tuple(
            _parse_journal_line(
                raw_line,
                index=line_index,
                entry_index=index,
                exercise_index=exercise_index,
            )
            for line_index, raw_line in enumerate(raw_lines)
        ),
    )


def _parse_closing(raw_closing: dict[str, Any], *, exercise_index: int) -> DemoClosing:
    if not isinstance(raw_closing, dict):
        raise ValidationError(
            {"demo": f"logical_exercises[{exercise_index}].closing must be an object."}
        )
    _assert_exact_keys(
        data=raw_closing,
        allowed={"closing_date", "reopening_date", "cash_actual", "inventory_actual"},
        context=f"logical_exercises[{exercise_index}].closing",
    )
    return DemoClosing(
        closing_date=_coerce_date(raw_closing["closing_date"], field="closing_date"),
        reopening_date=_coerce_date(raw_closing["reopening_date"], field="reopening_date"),
        cash_actual=(
            _coerce_decimal(raw_closing["cash_actual"], field="cash_actual")
            if raw_closing.get("cash_actual") is not None
            else None
        ),
        inventory_actual=(
            _coerce_decimal(raw_closing["inventory_actual"], field="inventory_actual")
            if raw_closing.get("inventory_actual") is not None
            else None
        ),
    )


def _parse_logical_exercise(raw_exercise: dict[str, Any], *, index: int) -> DemoLogicalExercise:
    if not isinstance(raw_exercise, dict):
        raise ValidationError({"demo": f"logical_exercises[{index}] must be an object."})
    _assert_exact_keys(
        data=raw_exercise,
        allowed={"journal_entries", "closing"},
        context=f"logical_exercises[{index}]",
    )
    raw_entries = raw_exercise.get("journal_entries")
    if not isinstance(raw_entries, list):
        raise ValidationError(
            {"demo": f"logical_exercises[{index}].journal_entries must be a list."}
        )
    return DemoLogicalExercise(
        journal_entries=tuple(
            _parse_journal_entry(raw_entry, index=entry_index, exercise_index=index)
            for entry_index, raw_entry in enumerate(raw_entries)
        ),
        closing=(
            _parse_closing(raw_exercise["closing"], exercise_index=index)
            if "closing" in raw_exercise and raw_exercise["closing"] is not None
            else None
        ),
    )


def parse_demo_payload(raw_payload: dict[str, Any]) -> DemoPayload:
    if not isinstance(raw_payload, dict):
        raise ValidationError({"demo": "The demo payload must be a JSON object."})

    _assert_exact_keys(
        data=raw_payload,
        allowed={
            "name",
            "description",
            "tax_id",
            "is_published",
            "opening_entry",
            "logical_exercises",
        },
        context="demo payload",
    )

    raw_logical_exercises = raw_payload.get("logical_exercises")
    if not isinstance(raw_logical_exercises, list) or not raw_logical_exercises:
        raise ValidationError(
            {"demo": "'logical_exercises' must be a non-empty list in the canonical demo format."}
        )

    opening_entry_raw = raw_payload.get("opening_entry")
    if not isinstance(opening_entry_raw, dict):
        raise ValidationError({"demo": "'opening_entry' must be an object."})

    opening_entry_payload = build_opening_entry_payload(data=opening_entry_raw)
    opening_entry = {
        "date": opening_entry_payload.date,
        "inventory_kind": opening_entry_payload.inventory_kind,
        "source_ref": opening_entry_payload.source_ref,
        "assets": [
            {
                "name": item.name,
                "parent_code": item.parent_code,
                "amount": item.amount,
            }
            for item in opening_entry_payload.assets
        ],
        "liabilities": [
            {
                "name": item.name,
                "parent_code": item.parent_code,
                "amount": item.amount,
            }
            for item in opening_entry_payload.liabilities
        ],
    }

    is_published = raw_payload.get("is_published", True)
    if not isinstance(is_published, bool):
        is_published = _coerce_bool(is_published, field="is_published")

    return DemoPayload(
        name=_coerce_str(raw_payload["name"], field="name").strip(),
        description=_coerce_str(raw_payload.get("description", ""), field="description"),
        tax_id=_coerce_str(raw_payload.get("tax_id", ""), field="tax_id"),
        is_published=is_published,
        opening_entry=opening_entry,
        logical_exercises=tuple(
            _parse_logical_exercise(raw_exercise, index=exercise_index)
            for exercise_index, raw_exercise in enumerate(raw_logical_exercises)
        ),
    )
