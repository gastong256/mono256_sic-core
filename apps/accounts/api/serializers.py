import re

from rest_framework import serializers

ACCOUNT_CODE_RE = re.compile(r"^[1-9]\.\d{2}\.\d{2}$")


class AccountCreateSerializer(serializers.Serializer):
    """Serializer for creating a new level-3 account under a company."""

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
        """Validate that the code matches the required X.XX.XX format."""
        if not ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Account code must match format X.XX.XX (e.g. 1.04.01)."
            )
        return value


class AccountUpdateSerializer(serializers.Serializer):
    """Serializer for partially updating a level-3 account (name and/or code)."""

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
        """Validate that the code matches the required X.XX.XX format."""
        if not ACCOUNT_CODE_RE.match(value):
            raise serializers.ValidationError(
                "Account code must match format X.XX.XX (e.g. 1.04.01)."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Ensure at least one field is provided."""
        if not attrs.get("name") and not attrs.get("code"):
            raise serializers.ValidationError(
                "At least one of 'name' or 'code' must be provided."
            )
        return attrs
