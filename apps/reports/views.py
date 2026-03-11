from datetime import date

import structlog
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies import selectors as company_selectors
from apps.reports.exports import (
    build_journal_book_workbook,
    build_ledger_workbook,
    build_trial_balance_workbook,
)
from apps.reports.exports.common import workbook_response
from apps.reports.serializers import LedgerParamsSerializer, ReportParamsSerializer
from apps.reports.services import journal_book, ledger, trial_balance

logger = structlog.get_logger(__name__)

_DATE_PARAMS = [
    OpenApiParameter(
        name="date_from",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Start date (YYYY-MM-DD). Defaults to the earliest entry date.",
        required=False,
    ),
    OpenApiParameter(
        name="date_to",
        type=str,
        location=OpenApiParameter.QUERY,
        description="End date (YYYY-MM-DD). Defaults to today.",
        required=False,
    ),
]


class ExcelExportUnavailable(APIException):
    status_code = 503
    default_code = "excel_export_unavailable"
    default_detail = "Excel export dependency is not installed. Install xlsxwriter."


def _ensure_excel_dependency() -> None:
    try:
        import xlsxwriter  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ExcelExportUnavailable() from exc


class JournalBookView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_journal_book",
        summary="Libro Diario",
        description=(
            "Chronological list of all posted journal entries for the company "
            "within the given date range, including all lines and grand totals."
        ),
        parameters=_DATE_PARAMS,
        responses={
            200: OpenApiResponse(description="Libro Diario report"),
            400: OpenApiResponse(description="Invalid query parameters"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)

        params = ReportParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = journal_book.get_journal_book(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
        )
        logger.debug("report_journal_book", company_id=company.pk, user=request.user.username)
        return Response(data)


class LedgerView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_ledger",
        summary="Libro Mayor",
        description=(
            "One card per level-3 account belonging to the company, showing every "
            "movement in the period chronologically with a running balance. "
            "Optionally filtered to a single account via account_id."
        ),
        parameters=_DATE_PARAMS + [
            OpenApiParameter(
                name="account_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter to a single level-3 account by its ID.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="Libro Mayor report"),
            400: OpenApiResponse(description="Invalid query parameters or account_id"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)

        params = LedgerParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = ledger.get_ledger(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
            account_id=params.validated_data.get("account_id"),
        )
        logger.debug("report_ledger", company_id=company.pk, user=request.user.username)
        return Response(data)


class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_trial_balance",
        summary="Balance de Comprobación",
        description=(
            "Two-level table: level-2 (colectiva) subtotal rows containing level-3 "
            "(subcuenta) rows, with total_debit, total_credit, and balance columns. "
            "Only accounts with movements in the period are included."
        ),
        parameters=_DATE_PARAMS,
        responses={
            200: OpenApiResponse(description="Balance de Comprobación report"),
            400: OpenApiResponse(description="Invalid query parameters"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)

        params = ReportParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = trial_balance.get_trial_balance(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
        )
        logger.debug("report_trial_balance", company_id=company.pk, user=request.user.username)
        return Response(data)


class JournalBookExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_journal_book_xlsx",
        summary="Export Libro Diario (XLSX)",
        parameters=_DATE_PARAMS,
        responses={
            200: OpenApiResponse(description="XLSX file", response=OpenApiTypes.BINARY),
            400: OpenApiResponse(description="Invalid query parameters"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        _ensure_excel_dependency()
        company = company_selectors.get_company(pk=company_id, user=request.user)
        params = ReportParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = journal_book.get_journal_book(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
        )
        filename = f"libro_diario_{company_id}_{date.today().isoformat()}.xlsx"
        artifact = build_journal_book_workbook(report=data)
        logger.info("report_journal_book_exported", company_id=company.pk, user=request.user.username)
        return workbook_response(artifact=artifact, filename=filename)


class LedgerExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_ledger_xlsx",
        summary="Export Libro Mayor (XLSX)",
        parameters=_DATE_PARAMS + [
            OpenApiParameter(
                name="account_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter to a single level-3 account by its ID.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(description="XLSX file", response=OpenApiTypes.BINARY),
            400: OpenApiResponse(description="Invalid query parameters or account_id"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        _ensure_excel_dependency()
        company = company_selectors.get_company(pk=company_id, user=request.user)
        params = LedgerParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = ledger.get_ledger(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
            account_id=params.validated_data.get("account_id"),
        )
        filename = f"libro_mayor_{company_id}_{date.today().isoformat()}.xlsx"
        artifact = build_ledger_workbook(report=data)
        logger.info("report_ledger_exported", company_id=company.pk, user=request.user.username)
        return workbook_response(artifact=artifact, filename=filename)


class TrialBalanceExcelExportView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="export_trial_balance_xlsx",
        summary="Export Balance de Comprobación (XLSX)",
        parameters=_DATE_PARAMS,
        responses={
            200: OpenApiResponse(description="XLSX file", response=OpenApiTypes.BINARY),
            400: OpenApiResponse(description="Invalid query parameters"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["reports"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        _ensure_excel_dependency()
        company = company_selectors.get_company(pk=company_id, user=request.user)
        params = ReportParamsSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)

        data = trial_balance.get_trial_balance(
            company=company,
            date_from=params.validated_data.get("date_from"),
            date_to=params.validated_data.get("date_to"),
        )
        filename = f"balance_comprobacion_{company_id}_{date.today().isoformat()}.xlsx"
        artifact = build_trial_balance_workbook(report=data)
        logger.info("report_trial_balance_exported", company_id=company.pk, user=request.user.username)
        return workbook_response(artifact=artifact, filename=filename)
