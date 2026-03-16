from rest_framework import serializers

from apps.companies.models import Company


class CompanySerializer(serializers.ModelSerializer):
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
        if hasattr(obj, "account_count"):
            return int(obj.account_count)
        return obj.accounts.count()


class CompanyWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, help_text="Company name.")
    tax_id = serializers.CharField(
        max_length=20,
        required=False,
        default="",
        allow_blank=True,
        help_text="Simulated CUIT (optional).",
    )


class CompanySelectorSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Company
        fields = ["id", "name", "owner_username"]
        read_only_fields = fields


class CompanySelectorListSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = CompanySelectorSerializer(many=True)
