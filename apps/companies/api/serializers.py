from rest_framework import serializers

from apps.companies.models import Company


class CompanySerializer(serializers.ModelSerializer):
    """Read serializer for Company instances."""

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    account_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "tax_id",
            "owner_username",
            "account_count",
            "books_closed_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "owner_username",
            "account_count",
            "books_closed_until",
            "created_at",
            "updated_at",
        ]

    def get_account_count(self, obj: Company) -> int:
        """Return the number of level-3 accounts linked to this company."""
        return obj.accounts.count()


class CompanyWriteSerializer(serializers.Serializer):
    """Write serializer for creating or updating a Company."""

    name = serializers.CharField(max_length=255, help_text="Company name.")
    tax_id = serializers.CharField(
        max_length=20,
        required=False,
        default="",
        allow_blank=True,
        help_text="Simulated CUIT (optional).",
    )
