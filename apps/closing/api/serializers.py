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


class CurrentBookBalancesParamsSerializer(serializers.Serializer):
    date_to = serializers.DateField(
        required=False,
        help_text="Optional cutoff date for the book balances. Defaults to today.",
    )


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
    active_exercise = serializers.DictField()
    previous_exercises = serializers.ListField()
    adjustments = serializers.DictField()
    result_summary = serializers.DictField()
    balance_sheet = serializers.DictField()
    income_statement = serializers.DictField()
    entries = serializers.DictField()


class SimplifiedClosingStateSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    books_closed_until = serializers.DateField(allow_null=True)
    last_patrimonial_closing_entry_id = serializers.IntegerField(allow_null=True)
    last_patrimonial_closing_date = serializers.DateField(allow_null=True)
    last_reopening_entry_id = serializers.IntegerField(allow_null=True)
    last_reopening_date = serializers.DateField(allow_null=True)
    current_exercise = serializers.DictField(allow_null=True)
    can_close = serializers.BooleanField()


class CurrentBookBalanceSummarySerializer(serializers.Serializer):
    parent_code = serializers.CharField()
    parent_name = serializers.CharField()
    total_debit = serializers.CharField()
    total_credit = serializers.CharField()
    book_balance = serializers.CharField()


class CurrentBookBalancesSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    as_of_date = serializers.DateField()
    books_closed_until = serializers.DateField(allow_null=True)
    cash = CurrentBookBalanceSummarySerializer()
    inventory = CurrentBookBalanceSummarySerializer()


class SimplifiedClosingExecuteSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    closing_date = serializers.DateField()
    reopening_date = serializers.DateField()
    books_closed_until = serializers.DateField()
    snapshot_id = serializers.IntegerField()
    created_entries = serializers.ListField()


class LogicalExerciseSerializer(serializers.Serializer):
    exercise_id = serializers.CharField()
    exercise_index = serializers.IntegerField()
    opening_entry_id = serializers.IntegerField()
    opening_source_type = serializers.CharField()
    start_date = serializers.DateField()
    closing_entry_id = serializers.IntegerField(allow_null=True)
    closing_date = serializers.DateField(allow_null=True)
    snapshot_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()


class LogicalExerciseListSerializer(serializers.Serializer):
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    current_exercise_id = serializers.CharField(allow_null=True)
    exercises = LogicalExerciseSerializer(many=True)


class ClosingSnapshotLineSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(allow_null=True)
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    root_code = serializers.CharField()
    parent_code = serializers.CharField()
    debit_balance = serializers.CharField()
    credit_balance = serializers.CharField()


class ClosingSnapshotSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    company_id = serializers.IntegerField()
    company = serializers.CharField()
    patrimonial_closing_entry_id = serializers.IntegerField()
    reopening_entry_id = serializers.IntegerField()
    closing_date = serializers.DateField()
    reopening_date = serializers.DateField()
    balance_sheet = serializers.DictField()
    income_statement = serializers.DictField()
    lines = ClosingSnapshotLineSerializer(many=True)
