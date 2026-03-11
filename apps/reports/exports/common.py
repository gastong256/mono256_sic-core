from __future__ import annotations

from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from typing import BinaryIO, Protocol

from django.http import FileResponse

EXCEL_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class SupportsClose(Protocol):
    def close(self) -> None: ...


@dataclass(frozen=True)
class WorkbookArtifact:
    workbook: SupportsClose
    stream: BinaryIO


def create_xlsx_stream() -> BinaryIO:
    return SpooledTemporaryFile(max_size=5 * 1024 * 1024, mode="w+b")


def workbook_response(*, artifact: WorkbookArtifact, filename: str) -> FileResponse:
    artifact.workbook.close()
    artifact.stream.seek(0)
    return FileResponse(
        artifact.stream,
        as_attachment=True,
        filename=filename,
        content_type=EXCEL_CONTENT_TYPE,
    )
