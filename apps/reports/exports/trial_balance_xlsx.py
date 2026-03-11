from __future__ import annotations

from apps.reports.exports.common import WorkbookArtifact, create_xlsx_stream


def build_trial_balance_workbook(*, report: dict) -> WorkbookArtifact:
    from xlsxwriter import Workbook

    stream = create_xlsx_stream()
    wb = Workbook(stream, {"constant_memory": True})
    ws = wb.add_worksheet("Balance")

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

    _write_row(["Balance de Comprobacion"], is_bold=True)
    _write_row([f"Empresa: {report['company']}"], is_bold=False)
    _write_row([f"Desde: {report['date_from']}  Hasta: {report['date_to']}"], is_bold=False)

    headers = [
        "Codigo",
        "Cuenta",
        "Tipo",
        "Debe",
        "Haber",
        "Saldo Deudor",
        "Saldo Acreedor",
    ]
    _write_row(headers, is_bold=True)

    for group in report.get("groups", []):
        _write_row(
            [
                group.get("account_code"),
                group.get("account_name"),
                group.get("account_type"),
                group.get("subtotal_debit"),
                group.get("subtotal_credit"),
                group.get("subtotal_debit_balance"),
                group.get("subtotal_credit_balance"),
            ],
            is_bold=True,
        )

        for account in group.get("accounts", []):
            _write_row(
                [
                    account.get("account_code"),
                    account.get("account_name"),
                    account.get("account_type"),
                    account.get("total_debit"),
                    account.get("total_credit"),
                    account.get("debit_balance"),
                    account.get("credit_balance"),
                ],
                is_bold=False,
            )

    _write_row([""], is_bold=False)
    totals = report.get("totals", {})
    _write_row(
        [
            "",
            "Totales",
            "",
            totals.get("total_debit", "0.00"),
            totals.get("total_credit", "0.00"),
            totals.get("total_debit_balance", "0.00"),
            totals.get("total_credit_balance", "0.00"),
        ],
        is_bold=True,
    )

    return WorkbookArtifact(workbook=wb, stream=stream)
