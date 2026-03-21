import re

from rest_framework import serializers

from apps.companies.opening import (
    OPENING_ASSET_PARENT_CODES,
    OPENING_LIABILITY_PARENT_CODES,
)
from apps.companies.models import Company
from apps.companies.services import viewer_can_write_company
from apps.journal.models import JournalEntry

PARENT_ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}$")


class CompanySerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    account_count = serializers.SerializerMethodField()
    has_opening_entry = serializers.SerializerMethodField()
    accounting_ready = serializers.SerializerMethodField()
    opening_entry_id = serializers.SerializerMethodField()
    viewer_can_write = serializers.SerializerMethodField()

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
            "is_published",
            "demo_slug",
            "viewer_can_write",
            "has_opening_entry",
            "accounting_ready",
            "opening_entry_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner_username",
            "account_count",
            "books_closed_until",
            "is_demo",
            "is_read_only",
            "is_published",
            "demo_slug",
            "viewer_can_write",
            "has_opening_entry",
            "accounting_ready",
            "opening_entry_id",
            "created_at",
            "updated_at",
        ]

    def get_account_count(self, obj: Company) -> int:
        if hasattr(obj, "account_count"):
            return int(obj.account_count)
        return obj.accounts.count()

    def get_has_opening_entry(self, obj: Company) -> bool:
        if hasattr(obj, "has_opening_entry"):
            return bool(obj.has_opening_entry)
        return obj.journal_entries.filter(source_type=JournalEntry.SourceType.OPENING).exists()

    def get_accounting_ready(self, obj: Company) -> bool:
        return self.get_has_opening_entry(obj)

    def get_opening_entry_id(self, obj: Company) -> int | None:
        opening_id = getattr(obj, "opening_entry_id", None)
        if opening_id is not None:
            return int(opening_id)
        return (
            obj.journal_entries.filter(source_type=JournalEntry.SourceType.OPENING)
            .values_list("id", flat=True)
            .first()
        )

    def get_viewer_can_write(self, obj: Company) -> bool:
        request = self.context.get("request")
        actor = getattr(request, "user", None) if request is not None else None
        return viewer_can_write_company(actor=actor, company=obj)


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


class CompanyOpeningAccountItemSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        help_text="Movement-account name to create or reuse for this company.",
    )
    parent_code = serializers.CharField(
        max_length=4,
        help_text="Parent colectiva code in format X.XX (e.g. 1.01).",
    )
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Positive amount.",
    )

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


class CompanyOpeningEntrySerializer(serializers.Serializer):
    date = serializers.DateField(help_text="Accounting date of the opening entry.")
    inventory_kind = serializers.ChoiceField(
        choices=[("INITIAL", "Inventario Inicial"), ("GENERAL", "Inventario General")],
        default="INITIAL",
        required=False,
        help_text="Whether the opening is based on the initial inventory or a later general inventory.",
    )
    source_ref = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
        help_text='Optional reference, e.g. "APERTURA-001" or "INV-GRAL-001".',
    )
    assets = CompanyOpeningAccountItemSerializer(
        many=True,
        min_length=1,
        help_text="Asset items that will be posted to Debe.",
    )
    liabilities = CompanyOpeningAccountItemSerializer(
        many=True,
        required=False,
        default=list,
        help_text="Liability items that will be posted to Haber.",
    )

    def _validate_unique_specs(self, *, value: list[dict], field_name: str) -> list[dict]:
        specs: set[tuple[str, str]] = set()
        for item in value:
            spec = (item["parent_code"], item["name"].strip().lower())
            if spec in specs:
                raise serializers.ValidationError(
                    f"Duplicate account definition in '{field_name}' for parent_code "
                    f"'{item['parent_code']}' and name '{item['name']}'."
                )
            specs.add(spec)
        return value

    def validate_assets(self, value: list[dict]) -> list[dict]:
        self._validate_unique_specs(value=value, field_name="assets")
        invalid_codes = sorted(
            {
                item["parent_code"]
                for item in value
                if item["parent_code"] not in OPENING_ASSET_PARENT_CODES
            }
        )
        if invalid_codes:
            raise serializers.ValidationError(
                f"Invalid asset parent_code(s) for opening: {', '.join(invalid_codes)}."
            )
        return value

    def validate_liabilities(self, value: list[dict]) -> list[dict]:
        self._validate_unique_specs(value=value, field_name="liabilities")
        invalid_codes = sorted(
            {
                item["parent_code"]
                for item in value
                if item["parent_code"] not in OPENING_LIABILITY_PARENT_CODES
            }
        )
        if invalid_codes:
            raise serializers.ValidationError(
                f"Invalid liability parent_code(s) for opening: {', '.join(invalid_codes)}."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        assets = attrs.get("assets") or []
        if not assets:
            raise serializers.ValidationError({"assets": "At least one asset is required."})
        return attrs


class CompanyCreateSerializer(CompanyWriteSerializer):
    opening_entry = CompanyOpeningEntrySerializer(
        required=False,
        help_text="Optional balanced opening entry to create the company with initial capital/assets.",
    )


class CompanySelectorSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    has_opening_entry = serializers.SerializerMethodField()
    accounting_ready = serializers.SerializerMethodField()
    viewer_can_write = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "owner_username",
            "is_demo",
            "is_read_only",
            "is_published",
            "demo_slug",
            "viewer_can_write",
            "has_opening_entry",
            "accounting_ready",
        ]
        read_only_fields = fields

    def get_has_opening_entry(self, obj: Company) -> bool:
        if hasattr(obj, "has_opening_entry"):
            return bool(obj.has_opening_entry)
        return obj.journal_entries.filter(source_type=JournalEntry.SourceType.OPENING).exists()

    def get_accounting_ready(self, obj: Company) -> bool:
        return self.get_has_opening_entry(obj)

    def get_viewer_can_write(self, obj: Company) -> bool:
        request = self.context.get("request")
        actor = getattr(request, "user", None) if request is not None else None
        return viewer_can_write_company(actor=actor, company=obj)


class CompanySelectorListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = CompanySelectorSerializer(many=True)


class DemoPublicationSerializer(serializers.Serializer):
    is_published = serializers.BooleanField(
        help_text="Whether the demo company should be globally visible in the application."
    )
