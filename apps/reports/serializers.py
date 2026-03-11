from rest_framework import serializers


class ReportParamsSerializer(serializers.Serializer):
    """Common date-range validation used across accounting reports."""

    date_from = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "Formato de fecha inválido. Use YYYY-MM-DD."},
    )
    date_to = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        error_messages={"invalid": "Formato de fecha inválido. Use YYYY-MM-DD."},
    )

    def validate(self, data: dict) -> dict:
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser posterior a la fecha de fin."
            )
        return data


class LedgerParamsSerializer(ReportParamsSerializer):
    """Report params + optional account filter for Libro Mayor."""

    account_id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "ID de cuenta inválido.",
            "min_value": "ID de cuenta inválido.",
        },
    )
