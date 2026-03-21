from __future__ import annotations

from apps.reports.exports.common import WorkbookArtifact, create_xlsx_stream


def build_closing_snapshot_workbook(*, snapshot: dict) -> WorkbookArtifact:
    from xlsxwriter import Workbook

    stream = create_xlsx_stream()
    wb = Workbook(stream, {"constant_memory": True})

    bold = wb.add_format({"bold": True})
    normal = wb.add_format()

    def _write_row(ws, row_idx: int, values: list[object], *, is_bold: bool = False) -> int:
        style = bold if is_bold else normal
        for col_idx, value in enumerate(values):
            if value is None:
                ws.write_blank(row_idx, col_idx, None, style)
            else:
                ws.write(row_idx, col_idx, value, style)
        return row_idx + 1

    summary = wb.add_worksheet("Resumen")
    row = 0
    row = _write_row(summary, row, ["Cierre Contable Confirmado"], is_bold=True)
    row = _write_row(summary, row, [f"Empresa: {snapshot['company']}"])
    row = _write_row(summary, row, [f"Snapshot ID: {snapshot['id']}"])
    row = _write_row(summary, row, [f"Fecha de cierre: {snapshot['closing_date']}"])
    row = _write_row(summary, row, [f"Fecha de reapertura: {snapshot['reopening_date']}"])
    row = _write_row(
        summary,
        row,
        [f"Asiento de cierre patrimonial: {snapshot['patrimonial_closing_entry_id']}"],
    )
    row = _write_row(summary, row, [f"Asiento de reapertura: {snapshot['reopening_entry_id']}"])

    net_result = snapshot.get("income_statement", {}).get("net_result", {})
    row = _write_row(summary, row, [""])
    row = _write_row(
        summary,
        row,
        ["Resultado neto", net_result.get("amount"), net_result.get("kind")],
        is_bold=True,
    )

    balance_sheet = wb.add_worksheet("Balance General")
    row = 0
    row = _write_row(balance_sheet, row, ["Balance General"], is_bold=True)
    row = _write_row(balance_sheet, row, [f"Empresa: {snapshot['company']}"])
    row = _write_row(balance_sheet, row, [f"Fecha: {snapshot['closing_date']}"])
    row = _write_row(balance_sheet, row, [""])
    row = _write_row(
        balance_sheet, row, ["Seccion", "Cuenta", "Subtotal", "Codigo", "Importe"], is_bold=True
    )

    bs = snapshot.get("balance_sheet", {})

    def _write_balance_section(section_label: str, section_payload: dict) -> int:
        nonlocal row
        for group in section_payload.get("groups", []):
            row = _write_row(
                balance_sheet,
                row,
                [
                    section_label,
                    group.get("account_name"),
                    group.get("subtotal"),
                    group.get("account_code"),
                    group.get("subtotal"),
                ],
                is_bold=True,
            )
            for account in group.get("accounts", []):
                row = _write_row(
                    balance_sheet,
                    row,
                    [
                        "",
                        account.get("account_name"),
                        "",
                        account.get("account_code"),
                        account.get("amount"),
                    ],
                )
        return row

    _write_balance_section("Activo", bs.get("assets", {}))
    _write_balance_section("Pasivo", bs.get("liabilities", {}))
    _write_balance_section("Patrimonio Neto", bs.get("equity", {}))

    derived_result = bs.get("equity", {}).get("derived_result")
    if derived_result:
        row = _write_row(
            balance_sheet,
            row,
            [
                "Patrimonio Neto",
                derived_result.get("name"),
                "",
                "3.02",
                derived_result.get("amount"),
            ],
            is_bold=True,
        )

    equation = bs.get("equation", {})
    row = _write_row(balance_sheet, row, [""])
    row = _write_row(
        balance_sheet,
        row,
        [
            "Totales",
            "",
            "",
            "Activo",
            equation.get("total_assets"),
        ],
        is_bold=True,
    )
    row = _write_row(
        balance_sheet,
        row,
        [
            "Totales",
            "",
            "",
            "Pasivo + PN",
            equation.get("total_liabilities_plus_equity"),
        ],
        is_bold=True,
    )
    row = _write_row(
        balance_sheet,
        row,
        ["Ecuacion balanceada", equation.get("is_balanced")],
        is_bold=True,
    )

    income = wb.add_worksheet("Estado Resultados")
    row = 0
    row = _write_row(income, row, ["Estado de Resultados"], is_bold=True)
    row = _write_row(income, row, [f"Empresa: {snapshot['company']}"])
    row = _write_row(income, row, [f"Fecha: {snapshot['closing_date']}"])
    row = _write_row(income, row, [""])
    row = _write_row(
        income, row, ["Seccion", "Cuenta", "Subtotal", "Codigo", "Importe"], is_bold=True
    )

    income_statement = snapshot.get("income_statement", {})

    def _write_income_section(section_label: str, section_payload: dict) -> int:
        nonlocal row
        for group in section_payload.get("accounts", []):
            row = _write_row(
                income,
                row,
                [
                    section_label,
                    group.get("account_name"),
                    group.get("subtotal"),
                    group.get("account_code"),
                    group.get("subtotal"),
                ],
                is_bold=True,
            )
            for account in group.get("accounts", []):
                row = _write_row(
                    income,
                    row,
                    [
                        "",
                        account.get("account_name"),
                        "",
                        account.get("account_code"),
                        account.get("amount"),
                    ],
                )
        row = _write_row(
            income,
            row,
            [section_label, "Total", "", "", section_payload.get("total")],
            is_bold=True,
        )
        return row

    _write_income_section("Resultados Positivos", income_statement.get("positive_results", {}))
    _write_income_section("Resultados Negativos", income_statement.get("negative_results", {}))
    row = _write_row(income, row, [""])
    row = _write_row(
        income,
        row,
        [
            "Resultado Neto",
            income_statement.get("net_result", {}).get("kind"),
            "",
            "",
            income_statement.get("net_result", {}).get("amount"),
        ],
        is_bold=True,
    )

    lines_ws = wb.add_worksheet("Saldos Patrimoniales")
    row = 0
    row = _write_row(lines_ws, row, ["Saldos Patrimoniales al Cierre"], is_bold=True)
    row = _write_row(lines_ws, row, [f"Empresa: {snapshot['company']}"])
    row = _write_row(lines_ws, row, [f"Fecha: {snapshot['closing_date']}"])
    row = _write_row(lines_ws, row, [""])
    row = _write_row(
        lines_ws,
        row,
        ["Codigo", "Cuenta", "Tipo", "Rubro", "Colectiva", "Saldo Deudor", "Saldo Acreedor"],
        is_bold=True,
    )
    for line in snapshot.get("lines", []):
        row = _write_row(
            lines_ws,
            row,
            [
                line.get("account_code"),
                line.get("account_name"),
                line.get("account_type"),
                line.get("root_code"),
                line.get("parent_code"),
                line.get("debit_balance"),
                line.get("credit_balance"),
            ],
        )

    return WorkbookArtifact(workbook=wb, stream=stream)
