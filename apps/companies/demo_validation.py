from __future__ import annotations

import datetime
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.companies.demo_schema import DemoPayload
from apps.companies.management.commands.load_chart_of_accounts import CHART
from apps.companies.opening import OPENING_ASSET_PARENT_CODES, OPENING_LIABILITY_PARENT_CODES
from apps.journal.models import JournalEntry, JournalEntryLine

_ZERO = Decimal("0")
_VALID_PARENT_CODES = frozenset(
    f"{root_code}{child_code}"
    for root_code, _root_name, _account_type, children in CHART
    for child_code, _child_name in children
)


def _validate_opening(payload: DemoPayload) -> None:
    opening = payload.opening_entry
    opening_date = opening["date"]
    if not isinstance(opening_date, datetime.date):
        raise ValidationError({"demo": "opening_entry.date must be a valid date."})

    if not opening["assets"]:
        raise ValidationError({"demo": "opening_entry.assets must contain at least one line."})

    assets_total = _ZERO
    liabilities_total = _ZERO
    for asset in opening["assets"]:
        if asset["parent_code"] not in OPENING_ASSET_PARENT_CODES:
            raise ValidationError(
                {
                    "demo": f"opening_entry asset parent_code '{asset['parent_code']}' is not allowed."
                }
            )
        if asset["amount"] <= _ZERO:
            raise ValidationError(
                {"demo": "opening_entry asset amounts must be greater than zero."}
            )
        assets_total += asset["amount"]

    for liability in opening["liabilities"]:
        if liability["parent_code"] not in OPENING_LIABILITY_PARENT_CODES:
            raise ValidationError(
                {
                    "demo": (
                        f"opening_entry liability parent_code '{liability['parent_code']}' "
                        "is not allowed."
                    )
                }
            )
        if liability["amount"] <= _ZERO:
            raise ValidationError(
                {"demo": "opening_entry liability amounts must be greater than zero."}
            )
        liabilities_total += liability["amount"]

    if assets_total - liabilities_total <= _ZERO:
        raise ValidationError(
            {"demo": "opening_entry must imply a positive initial capital balance."}
        )


def _validate_exercise_entries(payload: DemoPayload) -> None:
    expected_start = payload.opening_entry["date"]

    for exercise_index, exercise in enumerate(payload.logical_exercises):
        previous_date: datetime.date | None = None
        for entry_index, entry in enumerate(exercise.journal_entries):
            if entry.source_type != JournalEntry.SourceType.MANUAL:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}] "
                            "must use source_type=MANUAL."
                        )
                    }
                )
            if not entry.description:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}] "
                            "must have a non-empty description."
                        )
                    }
                )
            if previous_date and entry.date < previous_date:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}] must be ordered by ascending date."
                        )
                    }
                )
            if entry.date < expected_start:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}] contains an entry before the "
                            "exercise start date."
                        )
                    }
                )

            debit_total = _ZERO
            credit_total = _ZERO
            has_debit = False
            has_credit = False

            if not entry.lines:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}] "
                            "must contain at least one line."
                        )
                    }
                )

            for line_index, line in enumerate(entry.lines):
                if line.parent_code not in _VALID_PARENT_CODES:
                    raise ValidationError(
                        {
                            "demo": (
                                f"logical_exercises[{exercise_index}].journal_entries[{entry_index}]"
                                f".lines[{line_index}] uses unsupported parent_code "
                                f"'{line.parent_code}'."
                            )
                        }
                    )
                if not line.name:
                    raise ValidationError(
                        {
                            "demo": (
                                f"logical_exercises[{exercise_index}].journal_entries[{entry_index}]"
                                f".lines[{line_index}] must have a non-empty name."
                            )
                        }
                    )
                if line.amount <= _ZERO:
                    raise ValidationError(
                        {
                            "demo": (
                                f"logical_exercises[{exercise_index}].journal_entries[{entry_index}]"
                                f".lines[{line_index}] amount must be greater than zero."
                            )
                        }
                    )
                if line.type == JournalEntryLine.LineType.DEBIT:
                    debit_total += line.amount
                    has_debit = True
                elif line.type == JournalEntryLine.LineType.CREDIT:
                    credit_total += line.amount
                    has_credit = True
                else:
                    raise ValidationError(
                        {
                            "demo": (
                                f"logical_exercises[{exercise_index}].journal_entries[{entry_index}]"
                                f".lines[{line_index}] type must be DEBIT or CREDIT."
                            )
                        }
                    )

            if not has_debit or not has_credit:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}] "
                            "must contain at least one debit and one credit line."
                        )
                    }
                )
            if debit_total != credit_total:
                raise ValidationError(
                    {
                        "demo": (
                            f"logical_exercises[{exercise_index}].journal_entries[{entry_index}] "
                            "is not balanced."
                        )
                    }
                )

            previous_date = entry.date

        closing = exercise.closing
        is_last = exercise_index == len(payload.logical_exercises) - 1
        if closing is None:
            if not is_last:
                raise ValidationError(
                    {
                        "demo": (
                            "Every logical exercise except the last one must include a closing block."
                        )
                    }
                )
            continue

        if closing.reopening_date <= closing.closing_date:
            raise ValidationError(
                {
                    "demo": (
                        f"logical_exercises[{exercise_index}].closing must reopen after closing_date."
                    )
                }
            )
        if closing.closing_date < expected_start:
            raise ValidationError(
                {
                    "demo": (
                        f"logical_exercises[{exercise_index}].closing_date cannot be earlier than "
                        "the logical exercise start."
                    )
                }
            )
        if exercise.journal_entries and exercise.journal_entries[-1].date > closing.closing_date:
            raise ValidationError(
                {
                    "demo": (
                        f"logical_exercises[{exercise_index}] contains entries after its closing_date."
                    )
                }
            )
        expected_start = closing.reopening_date


def validate_demo_payload(payload: DemoPayload) -> None:
    if not payload.name:
        raise ValidationError({"demo": "'name' must not be blank."})
    if not payload.logical_exercises:
        raise ValidationError({"demo": "'logical_exercises' must not be empty."})
    _validate_opening(payload)
    _validate_exercise_entries(payload)
