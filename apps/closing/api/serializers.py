from rest_framework import serializers


class SimplifiedClosingRequestSerializer(serializers.Serializer):
    closing_date = serializers.DateField(
        help_text="Closing date for the simplified accounting close."
    )
    reopening_date = serializers.DateField(
        help_text="Reopening date for patrimonial balances; must be after closing_date."
    )
    cash_actual = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Optional physical cash count for arqueo.",
    )
    inventory_actual = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Optional physical inventory amount for mercaderías.",
    )

    def validate(self, attrs: dict) -> dict:
        if attrs["reopening_date"] <= attrs["closing_date"]:
            raise serializers.ValidationError(
                {"reopening_date": "Reopening date must be after the closing date."}
            )
        return attrs


class ClosingDraftLineSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(allow_null=True)
    account_code = serializers.CharField(allow_null=True)
    account_name = serializers.CharField()
    parent_code = serializers.CharField()
    type = serializers.CharField()
    amount = serializers.CharField()


class ClosingDraftEntrySerializer(serializers.Serializer):
    date = serializers.DateField()
    description = serializers.CharField()
    source_type = serializers.CharField()
    source_ref = serializers.CharField()
    total_debit = serializers.CharField()
    total_credit = serializers.CharField()
    lines = ClosingDraftLineSerializer(many=True)


class ClosingAdjustmentSummarySerializer(serializers.Serializer):
    book_balance = serializers.CharField(allow_null=True)
    actual_balance = serializers.CharField(allow_null=True)
    difference = serializers.CharField(allow_null=True)
    status = serializers.CharField()
    entry = ClosingDraftEntrySerializer(allow_null=True)


class SimplifiedClosingPreviewSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    closing_date = serializers.DateField()
    reopening_date = serializers.DateField()
    books_closed_until = serializers.DateField(allow_null=True)
    adjustments = serializers.DictField()
    result_summary = serializers.DictField()
    entries = serializers.DictField()


class SimplifiedClosingStateSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    books_closed_until = serializers.DateField(allow_null=True)
    last_patrimonial_closing_entry_id = serializers.IntegerField(allow_null=True)
    last_patrimonial_closing_date = serializers.DateField(allow_null=True)
    last_reopening_entry_id = serializers.IntegerField(allow_null=True)
    last_reopening_date = serializers.DateField(allow_null=True)
    can_close = serializers.BooleanField()


class SimplifiedClosingExecuteSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    closing_date = serializers.DateField()
    reopening_date = serializers.DateField()
    books_closed_until = serializers.DateField()
    created_entries = serializers.ListField()
