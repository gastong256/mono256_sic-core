import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from apps.closing.selectors import list_logical_exercises
from apps.companies.models import Company
from apps.users.models import User


def _demo_payload(*, amount: str = "100.00") -> dict:
    return {
        "name": "Empresa Demo Seed",
        "description": "Demo importada desde JSON.",
        "tax_id": "30-12345678-9",
        "opening_entry": {
            "date": "2026-03-16",
            "inventory_kind": "INITIAL",
            "source_ref": "DEMO-OPEN-001",
            "assets": [
                {"name": "Caja Principal", "parent_code": "1.01", "amount": amount},
            ],
        },
        "logical_exercises": [
            {
                "journal_entries": [
                    {
                        "date": "2026-03-20",
                        "description": "Venta demo",
                        "source_ref": "DEMO-JE-001",
                        "source_type": "MANUAL",
                        "lines": [
                            {
                                "parent_code": "1.01",
                                "name": "Caja Principal",
                                "type": "DEBIT",
                                "amount": amount,
                            },
                            {
                                "parent_code": "5.01",
                                "name": "Ventas Mostrador",
                                "type": "CREDIT",
                                "amount": amount,
                            },
                        ],
                    }
                ]
            }
        ],
    }


def _multi_exercise_demo_payload() -> dict:
    return {
        "name": "Empresa Demo Multiejercicio",
        "description": "Demo con dos ejercicios lógicos.",
        "tax_id": "30-12345678-0",
        "opening_entry": {
            "date": "2025-01-01",
            "inventory_kind": "INITIAL",
            "source_ref": "DEMO-OPEN-2025",
            "assets": [
                {"name": "Caja Principal", "parent_code": "1.01", "amount": "1000.00"},
                {"name": "Mercaderías Generales", "parent_code": "1.09", "amount": "500.00"},
            ],
            "liabilities": [
                {"name": "Proveedor Inicial", "parent_code": "2.01", "amount": "200.00"}
            ],
        },
        "logical_exercises": [
            {
                "journal_entries": [
                    {
                        "date": "2025-03-10",
                        "description": "Venta contado primer ejercicio",
                        "source_ref": "DEMO-2025-001",
                        "source_type": "MANUAL",
                        "lines": [
                            {
                                "parent_code": "1.01",
                                "name": "Caja Principal",
                                "type": "DEBIT",
                                "amount": "300.00",
                            },
                            {
                                "parent_code": "5.01",
                                "name": "Ventas Mostrador",
                                "type": "CREDIT",
                                "amount": "300.00",
                            },
                        ],
                    }
                ],
                "closing": {
                    "closing_date": "2025-12-31",
                    "reopening_date": "2026-01-01",
                    "cash_actual": "1280.00",
                    "inventory_actual": "470.00",
                },
            },
            {
                "journal_entries": [
                    {
                        "date": "2026-02-15",
                        "description": "Venta contado segundo ejercicio",
                        "source_ref": "DEMO-2026-001",
                        "source_type": "MANUAL",
                        "lines": [
                            {
                                "parent_code": "1.01",
                                "name": "Caja Principal",
                                "type": "DEBIT",
                                "amount": "220.00",
                            },
                            {
                                "parent_code": "5.01",
                                "name": "Ventas Mostrador",
                                "type": "CREDIT",
                                "amount": "220.00",
                            },
                        ],
                    }
                ],
            },
        ],
    }


@pytest.mark.django_db
class TestDemoImportCommand:
    def test_load_demo_company_from_file_is_idempotent(self, tmp_path: Path):
        call_command("load_chart_of_accounts")
        demo_file = tmp_path / "demo.json"
        demo_file.write_text(json.dumps(_demo_payload()), encoding="utf-8")

        call_command(
            "load_demo_company",
            "--file",
            str(demo_file),
            "--owner-username",
            "demo_seed_owner",
            "--publish",
        )
        call_command(
            "load_demo_company",
            "--file",
            str(demo_file),
            "--owner-username",
            "demo_seed_owner",
            "--publish",
        )

        assert Company.objects.filter(is_demo=True).count() == 1
        company = Company.objects.get(is_demo=True)
        assert company.is_read_only is True
        assert company.is_published is True
        assert company.demo_slug == "empresa-demo-seed"
        assert len(company.demo_content_sha256) == 64
        assert company.journal_entries.count() == 2
        owner = User.objects.get(username="demo_seed_owner")
        assert owner.role == User.Role.ADMIN

    def test_load_demo_company_from_r2_url_creates_new_slug_for_new_content(self):
        call_command("load_chart_of_accounts")

        first_response = Mock()
        first_response.raise_for_status.return_value = None
        first_response.json.return_value = _demo_payload(amount="100.00")

        second_response = Mock()
        second_response.raise_for_status.return_value = None
        second_response.json.return_value = _demo_payload(amount="200.00")

        with patch("apps.companies.demo_import.requests.get", return_value=first_response):
            call_command(
                "load_demo_company",
                "--r2-base-url",
                "https://demo.example.com",
                "--r2-key",
                "demo.json",
            )

        with patch("apps.companies.demo_import.requests.get", return_value=second_response):
            call_command(
                "load_demo_company",
                "--r2-base-url",
                "https://demo.example.com",
                "--r2-key",
                "demo.json",
            )

        slugs = list(
            Company.objects.filter(is_demo=True).order_by("id").values_list("demo_slug", flat=True)
        )
        assert slugs == ["empresa-demo-seed", "empresa-demo-seed-v2"]

    def test_load_demo_company_with_logical_exercises_creates_closed_and_open_cycles(
        self, tmp_path: Path
    ):
        call_command("load_chart_of_accounts")
        demo_file = tmp_path / "demo-multi.json"
        demo_file.write_text(json.dumps(_multi_exercise_demo_payload()), encoding="utf-8")

        call_command("load_demo_company", "--file", str(demo_file))

        company = Company.objects.get(is_demo=True, name="Empresa Demo Multiejercicio")
        exercises = list_logical_exercises(company=company)

        assert len(exercises) == 2
        assert exercises[0].status == "closed"
        assert exercises[0].start_date.isoformat() == "2025-01-01"
        assert exercises[0].closing_date.isoformat() == "2025-12-31"
        assert exercises[1].status == "open"
        assert exercises[1].opening_source_type == "REOPENING"
        assert exercises[1].start_date.isoformat() == "2026-01-01"
        assert company.journal_entries.filter(source_type="REOPENING").count() == 1
        assert company.journal_entries.filter(source_type="PATRIMONIAL_CLOSING").count() == 1

    def test_invalid_demo_payload_is_skipped_without_writing(self, tmp_path: Path, capsys):
        call_command("load_chart_of_accounts")
        invalid_demo = {
            "name": "Demo Inválida",
            "description": "Shape viejo no soportado.",
            "tax_id": "30-00000000-0",
            "opening_entry": {
                "date": "2026-01-01",
                "inventory_kind": "INITIAL",
                "source_ref": "INVALID-OPEN",
                "assets": [{"name": "Caja Principal", "parent_code": "1.01", "amount": "100.00"}],
                "liabilities": [],
            },
            "journal_entries": [],
        }
        demo_file = tmp_path / "invalid-demo.json"
        demo_file.write_text(json.dumps(invalid_demo), encoding="utf-8")

        call_command("load_demo_company", "--file", str(demo_file))

        captured = capsys.readouterr()
        assert "Skipping import" in captured.out
        assert Company.objects.filter(name="Demo Inválida").count() == 0

    def test_invalid_logical_exercise_chain_is_skipped_without_writing(
        self, tmp_path: Path, capsys
    ):
        call_command("load_chart_of_accounts")
        invalid_demo = {
            "name": "Demo Cadena Inválida",
            "description": "Dos ejercicios sin cierre intermedio.",
            "tax_id": "30-00000000-1",
            "opening_entry": {
                "date": "2025-01-01",
                "inventory_kind": "INITIAL",
                "source_ref": "INVALID-CHAIN-OPEN",
                "assets": [{"name": "Caja Principal", "parent_code": "1.01", "amount": "100.00"}],
                "liabilities": [],
            },
            "logical_exercises": [
                {
                    "journal_entries": [
                        {
                            "date": "2025-03-01",
                            "description": "Venta 1",
                            "source_type": "MANUAL",
                            "source_ref": "INVALID-1",
                            "lines": [
                                {
                                    "parent_code": "1.01",
                                    "name": "Caja Principal",
                                    "type": "DEBIT",
                                    "amount": "100.00",
                                },
                                {
                                    "parent_code": "5.01",
                                    "name": "Ventas Mostrador",
                                    "type": "CREDIT",
                                    "amount": "100.00",
                                },
                            ],
                        }
                    ]
                },
                {
                    "journal_entries": [
                        {
                            "date": "2026-02-01",
                            "description": "Venta 2",
                            "source_type": "MANUAL",
                            "source_ref": "INVALID-2",
                            "lines": [
                                {
                                    "parent_code": "1.01",
                                    "name": "Caja Principal",
                                    "type": "DEBIT",
                                    "amount": "120.00",
                                },
                                {
                                    "parent_code": "5.01",
                                    "name": "Ventas Mostrador",
                                    "type": "CREDIT",
                                    "amount": "120.00",
                                },
                            ],
                        }
                    ]
                },
            ],
        }
        demo_file = tmp_path / "invalid-chain.json"
        demo_file.write_text(json.dumps(invalid_demo), encoding="utf-8")

        call_command("load_demo_company", "--file", str(demo_file))

        captured = capsys.readouterr()
        assert "Skipping import" in captured.out
        assert Company.objects.filter(name="Demo Cadena Inválida").count() == 0
