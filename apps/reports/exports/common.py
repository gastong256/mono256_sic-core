from __future__ import annotations

from io import BytesIO

from django.http import HttpResponse

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def workbook_response(*, workbook: object, filename: str) -> HttpResponse:
    stream = BytesIO()
    workbook.save(stream)  # type: ignore[attr-defined]
    stream.seek(0)
    response = HttpResponse(stream.getvalue(), content_type=EXCEL_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
