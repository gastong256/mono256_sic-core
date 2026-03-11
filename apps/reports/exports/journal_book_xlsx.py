from __future__ import annotations

from apps.reports.exports.common import WorkbookArtifact, create_xlsx_stream


def build_journal_book_workbook(*, report: dict) -> WorkbookArtifact:
    from xlsxwriter import Workbook

    stream = create_xlsx_stream()
    wb = Workbook(stream, {"constant_memory": True})
    ws = wb.add_worksheet("Libro Diario")

    bold = wb.add_format({"bold": True})
    normal = wb.add_format()

    row_idx = 0

    def _write_row(values: list[object], *, is_bold: bool) -> None:
        nonlocal row_idx
        style = bold if is_bold else normal
        for col_idx, value in enumerate(values):
            if value is None:
                ws.write_blank(row_idx, col_idx, None, style)
            else:
                ws.write(row_idx, col_idx, value, style)
        row_idx += 1

    _write_row(["Libro Diario"], is_bold=True)
    _write_row([f"Empresa: {report['company']}"], is_bold=False)
    _write_row([f"Desde: {report['date_from']}  Hasta: {report['date_to']}"], is_bold=False)

    headers = ["Asiento", "Fecha", "Descripcion", "Referencia", "Cuenta", "Debe", "Haber"]
    _write_row(headers, is_bold=True)

    for entry in report.get("entries", []):
        for line in entry.get("lines", []):
            _write_row(
                [
                    entry.get("entry_number"),
                    entry.get("date"),
                    entry.get("description"),
                    entry.get("source_ref"),
                    f"{line.get('account_code')} - {line.get('account_name')}",
                    line.get("debit"),
                    line.get("credit"),
                ],
                is_bold=False,
            )

        _write_row(
            [
                "",
                "",
                "Subtotal asiento",
                "",
                "",
                entry.get("total_debit"),
                entry.get("total_credit"),
            ],
            is_bold=True,
        )
        _write_row([""], is_bold=False)

    _write_row(
        [
            "",
            "",
            "Totales",
            "",
            "",
            report.get("totals", {}).get("total_debit", "0.00"),
            report.get("totals", {}).get("total_credit", "0.00"),
        ],
        is_bold=True,
    )

    return WorkbookArtifact(workbook=wb, stream=stream)
