import structlog
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies import selectors as company_selectors
from apps.journal import selectors, services
from apps.journal.api.serializers import (
    JournalEntryCreateSerializer,
    JournalEntryDetailSerializer,
    JournalEntryListSerializer,
)

logger = structlog.get_logger(__name__)


class JournalEntryListCreateView(APIView):
    """List journal entries for a company, or create and post a new one."""

    permission_classes = [IsAuthenticated]

    def _get_company(self, company_id: int, user):
        return company_selectors.get_company(pk=company_id, user=user)

    @extend_schema(
        operation_id="list_journal_entries",
        summary="List journal entries",
        description="Returns all journal entries for the given company ordered by entry number.",
        responses={
            200: JournalEntryListSerializer(many=True),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["journal"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = self._get_company(company_id, request.user)
        entries = selectors.list_journal_entries(company=company)
        return Response(JournalEntryListSerializer(entries, many=True).data)

    @extend_schema(
        operation_id="create_journal_entry",
        summary="Create and post a journal entry",
        description=(
            "Creates a new journal entry and immediately posts it. "
            "Debits must equal credits. All accounts must belong to this company."
        ),
        request=JournalEntryCreateSerializer,
        responses={
            201: JournalEntryDetailSerializer,
            400: OpenApiResponse(description="Validation or business rule error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["journal"],
    )
    def post(self, request: Request, company_id: int) -> Response:
        company = self._get_company(company_id, request.user)

        serializer = JournalEntryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = services.create_journal_entry(
            company=company,
            created_by=request.user,
            **serializer.validated_data,
        )
        logger.info(
            "journal_entry_created",
            entry_id=entry.pk,
            entry_number=entry.entry_number,
            company_id=company.pk,
            user=request.user.username,
        )
        entry_with_lines = selectors.get_journal_entry(pk=entry.pk, company=company)
        return Response(JournalEntryDetailSerializer(entry_with_lines).data, status=status.HTTP_201_CREATED)


class JournalEntryDetailView(APIView):
    """Retrieve a single journal entry with its lines."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="get_journal_entry",
        summary="Retrieve a journal entry",
        description="Returns full detail of a journal entry including all lines.",
        responses={
            200: JournalEntryDetailSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company or entry not found"),
        },
        tags=["journal"],
    )
    def get(self, request: Request, company_id: int, entry_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        entry = selectors.get_journal_entry(pk=entry_id, company=company)
        return Response(JournalEntryDetailSerializer(entry).data)
