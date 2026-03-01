from rest_framework import serializers

from apps.example.models import Item


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]

    class JSONAPIMeta:
        resource_name = "items"


class ItemCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        help_text="Human-readable item name.",
    )
    description = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        help_text="Optional description.",
    )

    class Meta:
        openapi_examples = {
            "minimal": {
                "summary": "Minimal item",
                "value": {"name": "Widget"},
            },
            "full": {
                "summary": "Full item",
                "value": {"name": "Widget", "description": "A useful widget."},
            },
        }
