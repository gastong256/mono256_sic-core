from __future__ import annotations

from apps.reports.exports.common import WorkbookArtifact, create_xlsx_stream


def build_ledger_workbook(*, report: dict) -> WorkbookArtifact:
    from xlsxwriter import Workbook

    stream = create_xlsx_stream()
    wb = Workbook(stream, {"constant_memory": True})
    ws = wb.add_worksheet("Libro Mayor")

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

    _write_row(["Libro Mayor"], is_bold=True)
    _write_row([f"Empresa: {report['company']}"], is_bold=False)
    _write_row([f"Desde: {report['date_from']}  Hasta: {report['date_to']}"], is_bold=False)
    _write_row([""], is_bold=False)

    headers = ["Fecha", "Asiento", "Descripcion", "Referencia", "Debe", "Haber", "Saldo"]

    for account in report.get("accounts", []):
        _write_row(
            [
                f"{account.get('account_code')} - {account.get('account_name')}",
                f"Tipo: {account.get('account_type')}",
                f"Saldo normal: {account.get('normal_balance')}",
            ],
            is_bold=True,
        )

        _write_row(["Saldo inicial", "", "", "", "", account.get("opening_balance")], is_bold=False)
        _write_row(headers, is_bold=True)

        for move in account.get("movements", []):
            _write_row(
                [
                    move.get("date"),
                    move.get("entry_number"),
                    move.get("description"),
                    move.get("source_ref"),
                    move.get("debit"),
                    move.get("credit"),
                    move.get("balance"),
                ],
                is_bold=False,
            )

        _write_row(
            [
                "",
                "",
                "Totales periodo",
                "",
                account.get("period_totals", {}).get("total_debit", "0.00"),
                account.get("period_totals", {}).get("total_credit", "0.00"),
                account.get("closing_balance"),
            ],
            is_bold=True,
        )
        _write_row([""], is_bold=False)

    return WorkbookArtifact(workbook=wb, stream=stream)
