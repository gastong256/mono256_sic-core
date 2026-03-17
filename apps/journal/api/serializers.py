from rest_framework import serializers

from apps.journal.models import JournalEntry, JournalEntryLine


class JournalEntryLineReadSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.full_code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = ["account_id", "account_code", "account_name", "type", "amount"]
        read_only_fields = fields


class JournalEntryLineWriteSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(help_text="ID of the level-3 account.")
    type = serializers.ChoiceField(
        choices=JournalEntryLine.LineType.choices,
        help_text="DEBIT or CREDIT.",
    )
    amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Positive amount.",
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("El importe de cada línea debe ser mayor a cero.")
        return value


class JournalEntryListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    total_debit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    reversal_of_id = serializers.IntegerField(read_only=True)
    reversed_by_id = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "entry_number",
            "date",
            "description",
            "source_type",
            "source_ref",
            "created_by",
            "reversal_of_id",
            "reversed_by_id",
            "total_debit",
            "total_credit",
        ]
        read_only_fields = fields

    def get_reversed_by_id(self, obj: JournalEntry) -> int | None:
        try:
            return obj.reversed_by.id
        except JournalEntry.reversed_by.RelatedObjectDoesNotExist:
            return None


class JournalEntryDetailSerializer(JournalEntryListSerializer):
    lines = JournalEntryLineReadSerializer(many=True, read_only=True)

    class Meta(JournalEntryListSerializer.Meta):
        fields = JournalEntryListSerializer.Meta.fields + ["lines"]
        read_only_fields = fields


class JournalEntryListPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = JournalEntryListSerializer(many=True)


class JournalEntryCreateSerializer(serializers.Serializer):
    date = serializers.DateField(help_text="Accounting date of the entry.")
    description = serializers.CharField(
        max_length=500,
        help_text="Glosa / description of the entry.",
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
        help_text='E.g. "Factura A-0001".',
    )
    lines = JournalEntryLineWriteSerializer(
        many=True,
        help_text="At least one DEBIT and one CREDIT line, balanced.",
    )

    def validate_source_type(self, value: str) -> str:
        if value == JournalEntry.SourceType.OPENING:
            raise serializers.ValidationError(
                "Opening entries must be created through the company opening-entry flow."
            )
        return value

    def validate_lines(self, value: list) -> list:
        if len(value) < 2:
            raise serializers.ValidationError(
                "El asiento debe tener al menos una línea deudora y una acreedora."
            )
        return value


class JournalEntryReverseSerializer(serializers.Serializer):
    date = serializers.DateField(required=False, help_text="Date for the reversal entry.")
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional description for the reversal entry.",
    )
