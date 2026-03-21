from __future__ import annotations

from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol

from django.http import FileResponse
from rest_framework.exceptions import APIException

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class SupportsClose(Protocol):
    def close(self) -> None: ...


@dataclass(frozen=True)
class WorkbookArtifact:
    workbook: SupportsClose
    stream: BinaryIO


class ExcelExportUnavailable(APIException):
    status_code = 503
    default_code = "excel_export_unavailable"
    default_detail = "Excel export dependency is not installed. Install xlsxwriter."


def create_xlsx_stream() -> BinaryIO:
    return SpooledTemporaryFile(max_size=5 * 1024 * 1024, mode="w+b")


def ensure_excel_dependency() -> None:
    try:
        import xlsxwriter  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ExcelExportUnavailable() from exc


def workbook_response(*, artifact: WorkbookArtifact, filename: str) -> FileResponse:
    artifact.workbook.close()
    artifact.stream.seek(0)
    return FileResponse(
        artifact.stream,
        as_attachment=True,
        filename=filename,
        content_type=EXCEL_CONTENT_TYPE,
    )
