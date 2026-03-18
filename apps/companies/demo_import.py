import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from django.db import transaction
from django.utils.text import slugify

from apps.companies.account_resolution import (
    MovementAccountResolutionSpec,
    account_resolution_key,
    resolve_company_movement_accounts,
)
from apps.companies.demo_schema import DemoPayload, parse_demo_payload
from apps.companies.demo_validation import validate_demo_payload
from apps.companies.models import Company
from apps.companies.services import create_company_with_optional_opening
from apps.journal import services as journal_services
from apps.users.models import User


@dataclass(frozen=True)
class DemoImportSource:
    label: str
    payload: dict[str, Any]
    canonical_json: str
    sha256: str


def _canonicalize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _build_source(*, label: str, payload: dict[str, Any]) -> DemoImportSource:
    canonical_json = _canonicalize_payload(payload)
    return DemoImportSource(
        label=label,
        payload=payload,
        canonical_json=canonical_json,
        sha256=hashlib.sha256(canonical_json.encode("utf-8")).hexdigest(),
    )


def load_demo_source_from_file(*, file_path: str) -> DemoImportSource:
    path = Path(file_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _build_source(label=str(path), payload=payload)


def load_demo_source_from_url(*, url: str, timeout: int = 15) -> DemoImportSource:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return _build_source(label=url, payload=payload)


def build_demo_url(*, base_url: str, key: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", key.lstrip("/"))


def get_or_create_demo_owner(*, username: str) -> User:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": False},
    )
    updated_fields: list[str] = []
    if user.role != User.Role.ADMIN:
        user.role = User.Role.ADMIN
        updated_fields.append("role")
    if not user.is_staff:
        user.is_staff = True
        updated_fields.append("is_staff")
    if created:
        user.set_unusable_password()
        user.save()
        return user
    if updated_fields:
        user.save(update_fields=updated_fields)
    return user


def _build_demo_slug(*, name: str) -> str:
    base = slugify(name) or "demo"
    if not Company.objects.filter(is_demo=True, demo_slug=base).exists():
        return base

    version = 2
    while Company.objects.filter(is_demo=True, demo_slug=f"{base}-v{version}").exists():
        version += 1
    return f"{base}-v{version}"


def _resolve_demo_entry_accounts(
    *, company: Company, actor: User, lines: tuple[Any, ...]
) -> list[dict]:
    specs = [
        MovementAccountResolutionSpec(
            parent_code=line.parent_code,
            name=line.name,
        )
        for line in lines
    ]
    accounts_by_key = resolve_company_movement_accounts(company=company, actor=actor, specs=specs)
    resolved_lines = []
    for line in lines:
        resolved_lines.append(
            {
                "account_id": accounts_by_key[
                    account_resolution_key(parent_code=line.parent_code, name=line.name)
                ].id,
                "type": line.type,
                "amount": Decimal(str(line.amount)),
            }
        )
    return resolved_lines


def _import_demo_journal_entries(
    *, company: Company, actor: User, entries: tuple[Any, ...]
) -> list[int]:
    created_entry_ids: list[int] = []
    for entry_data in entries:
        resolved_lines = _resolve_demo_entry_accounts(
            company=company,
            actor=actor,
            lines=entry_data.lines,
        )
        entry = journal_services.create_journal_entry(
            company=company,
            created_by=actor,
            date=entry_data.date,
            description=entry_data.description,
            source_type=entry_data.source_type,
            source_ref=entry_data.source_ref,
            lines=resolved_lines,
        )
        created_entry_ids.append(entry.id)
    return created_entry_ids


def _normalize_closing_payload(closing_payload: Any) -> dict[str, Any]:
    normalized = {
        "closing_date": closing_payload.closing_date,
        "reopening_date": closing_payload.reopening_date,
    }
    if closing_payload.cash_actual is not None:
        normalized["cash_actual"] = Decimal(str(closing_payload.cash_actual))
    if closing_payload.inventory_actual is not None:
        normalized["inventory_actual"] = Decimal(str(closing_payload.inventory_actual))
    return normalized


def _import_logical_exercises_demo_activity(
    *, company: Company, actor: User, payload: DemoPayload
) -> None:
    from apps.closing.services import execute_simplified_closing

    for exercise in payload.logical_exercises:
        _import_demo_journal_entries(
            company=company,
            actor=actor,
            entries=exercise.journal_entries,
        )
        if exercise.closing:
            execute_simplified_closing(
                company=company,
                actor=actor,
                data=_normalize_closing_payload(exercise.closing),
            )


@transaction.atomic
def import_demo_company(
    *,
    source: DemoImportSource,
    owner_username: str = "demo_owner",
    publish_override: bool | None = None,
) -> tuple[Company, bool]:
    existing = Company.objects.filter(
        is_demo=True,
        demo_content_sha256=source.sha256,
    ).first()
    if existing is not None:
        return existing, False

    parsed_payload = parse_demo_payload(source.payload)
    validate_demo_payload(parsed_payload)
    owner = get_or_create_demo_owner(username=owner_username)
    name = parsed_payload.name

    company = create_company_with_optional_opening(
        name=name,
        description=parsed_payload.description,
        tax_id=parsed_payload.tax_id,
        owner=owner,
        opening_entry=parsed_payload.opening_entry,
    )

    _import_logical_exercises_demo_activity(company=company, actor=owner, payload=parsed_payload)

    company.is_demo = True
    company.is_read_only = True
    company.is_published = (
        bool(publish_override) if publish_override is not None else parsed_payload.is_published
    )
    company.demo_slug = _build_demo_slug(name=name)
    company.demo_content_sha256 = source.sha256
    company.full_clean()
    company.save(
        update_fields=[
            "is_demo",
            "is_read_only",
            "is_published",
            "demo_slug",
            "demo_content_sha256",
            "updated_at",
        ]
    )

    return company, True
