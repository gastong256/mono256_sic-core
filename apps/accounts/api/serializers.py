import re

from rest_framework import serializers

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


class AccountCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        help_text="Human-readable account name.",
    )
    code = serializers.CharField(
        max_length=10,
        help_text="Full account code in format X.XX.XX (e.g. 1.04.01).",
    )
    parent_id = serializers.IntegerField(
        help_text="ID of the parent level-2 account (colectiva).",
    )

    def validate_code(self, value: str) -> str:
        if not ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Account code must match format X.XX.XX (e.g. 1.04.01)."
            )
        return value


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        required=False,
        help_text="New account name.",
    )
    code = serializers.CharField(
        max_length=10,
        required=False,
        help_text="New full account code in format X.XX.XX (e.g. 1.04.02).",
    )

    def validate_code(self, value: str) -> str:
        if not ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Account code must match format X.XX.XX (e.g. 1.04.01)."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("name") and not attrs.get("code"):
            raise serializers.ValidationError("At least one of 'name' or 'code' must be provided.")
        return attrs


class AccountVisibilityUpdateSerializer(serializers.Serializer):
    is_visible = serializers.BooleanField()
    teacher_id = serializers.IntegerField(required=False, min_value=1)


class AccountVisibilityBulkItemSerializer(serializers.Serializer):
    account_id = serializers.IntegerField(min_value=1)
    is_visible = serializers.BooleanField()


class AccountVisibilityBulkUpdateSerializer(serializers.Serializer):
    teacher_id = serializers.IntegerField(required=False, min_value=1)
    updates = AccountVisibilityBulkItemSerializer(many=True, min_length=1)

    def validate_updates(self, value: list[dict]) -> list[dict]:
        seen: set[int] = set()
        for item in value:
            account_id = int(item["account_id"])
            if account_id in seen:
                raise serializers.ValidationError(
                    f"Duplicate account_id in batch payload: {account_id}."
                )
            seen.add(account_id)
        return value


class AccountVisibilityBootstrapSerializer(serializers.Serializer):
    selected_teacher_id = serializers.IntegerField(allow_null=True)
    teachers = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    chart = serializers.ListField(child=serializers.DictField(), allow_empty=True)
