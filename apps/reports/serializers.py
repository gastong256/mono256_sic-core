from rest_framework import serializers


class ReportParamsSerializer(serializers.Serializer):
    """Shared query-parameter validator for all three report endpoints."""

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
    """Query-parameter validator for the Libro Mayor endpoint."""

    account_id = serializers.IntegerField(
        required=False,
        min_value=1,
        error_messages={
            "invalid": "ID de cuenta inválido.",
            "min_value": "ID de cuenta inválido.",
        },
    )
