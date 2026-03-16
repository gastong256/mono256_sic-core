import re

from rest_framework import serializers

from apps.companies.models import Company
from apps.journal.models import JournalEntry, JournalEntryLine

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")
PARENT_ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}$")


class CompanySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    account_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "description",
            "tax_id",
            "owner_username",
            "account_count",
            "books_closed_until",
            "is_demo",
            "is_read_only",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "description",
            "owner_username",
            "account_count",
            "books_closed_until",
            "is_demo",
            "is_read_only",
            "created_at",
            "updated_at",
        ]

    def get_account_count(self, obj: Company) -> int:
        if hasattr(obj, "account_count"):
            return int(obj.account_count)
        return obj.accounts.count()


class CompanyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, help_text="Company name.")
    description = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        help_text="Optional business description.",
    )
    tax_id = serializers.CharField(
        max_length=20,
        required=False,
        default="",
        allow_blank=True,
        help_text="Simulated CUIT (optional).",
    )


class CompanyOpeningLineSerializer(serializers.Serializer):
    code = serializers.CharField(
        max_length=10,
        help_text="Full account code in format X.XX.XX (e.g. 1.01.01).",
    )
    name = serializers.CharField(
        max_length=255,
        help_text="Movement-account name to create or reuse for this company.",
    )
    parent_code = serializers.CharField(
        max_length=4,
        help_text="Parent colectiva code in format X.XX (e.g. 1.01).",
    )
    type = serializers.ChoiceField(
        choices=JournalEntryLine.LineType.choices,
        help_text="DEBIT or CREDIT.",
    )
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Positive amount.",
    )

    def validate_code(self, value: str) -> str:
        if not ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Account code must match format X.XX.XX (e.g. 1.04.01)."
            )
        return value

    def validate_parent_code(self, value: str) -> str:
        if not PARENT_ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Parent account code must match format X.XX (e.g. 1.04)."
            )
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El importe de cada línea debe ser mayor a cero.")
        return value

    def validate(self, attrs: dict) -> dict:
        code = attrs["code"]
        parent_code = attrs["parent_code"]
        expected_prefix = f"{parent_code}."
        if not code.startswith(expected_prefix):
            raise serializers.ValidationError(
                {"code": f"Account code must start with '{expected_prefix}'."}
            )
        return attrs


class CompanyOpeningEntrySerializer(serializers.Serializer):
    date = serializers.DateField(help_text="Accounting date of the opening entry.")
    description = serializers.CharField(
        max_length=500,
        help_text="Glosa / description of the opening entry.",
    )
    source_type = serializers.ChoiceField(
        choices=JournalEntry.SourceType.choices,
        default=JournalEntry.SourceType.MANUAL,
        required=False,
    )
    source_ref = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
        help_text='Optional reference, e.g. "APERTURA-001".',
    )
    lines = CompanyOpeningLineSerializer(
        many=True,
        min_length=2,
        help_text="Opening lines with per-line account creation metadata.",
    )

    def validate_lines(self, value: list[dict]) -> list[dict]:
        specs_by_code: dict[str, tuple[str, str]] = {}
        for item in value:
            code = item["code"]
            spec = (item["name"], item["parent_code"])
            previous = specs_by_code.get(code)
            if previous and previous != spec:
                raise serializers.ValidationError(
                    f"Opening line account '{code}' must use the same name and parent_code."
                )
            specs_by_code[code] = spec
        return value


class CompanyCreateSerializer(CompanyWriteSerializer):
    opening_entry = CompanyOpeningEntrySerializer(
        required=False,
        help_text="Optional balanced opening entry to create the company with initial capital/assets.",
    )


class CompanySelectorSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Company
        fields = ["id", "name", "owner_username", "is_demo", "is_read_only"]
        read_only_fields = fields


class CompanySelectorListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = CompanySelectorSerializer(many=True)
