import structlog
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate_queryset
from apps.companies import selectors as company_selectors
from apps.journal import selectors, services
from apps.journal.api.serializers import (
    JournalEntryCreateSerializer,
    JournalEntryDetailSerializer,
    JournalEntryListPaginatedSerializer,
    JournalEntryListSerializer,
    JournalEntryReverseSerializer,
)

logger = structlog.get_logger(__name__)


class JournalEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_company(self, company_id: int, user):
        return company_selectors.get_company(pk=company_id, user=user)

    @extend_schema(
        operation_id="list_journal_entries",
        summary="List journal entries",
        description="Returns paginated journal entries for the company ordered by entry number.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Pagination page number.",
            ),
        ],
        responses={
            200: JournalEntryListPaginatedSerializer,
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["journal"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        company = self._get_company(company_id, request.user)
        entries_qs = selectors.list_journal_entries(company=company)
        paginator, page = paginate_queryset(request=request, queryset=entries_qs)
        data = JournalEntryListSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

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
            409: OpenApiResponse(
                description="Closed period, read-only demo company, or concurrent conflict"
            ),
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
        return Response(
            JournalEntryDetailSerializer(entry_with_lines).data, status=status.HTTP_201_CREATED
        )


class JournalEntryDetailView(APIView):
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


class JournalEntryReverseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="reverse_journal_entry",
        summary="Reverse a journal entry",
        description="Creates a full contra-entry (debits<->credits) and links it to the original entry.",
        request=JournalEntryReverseSerializer,
        responses={
            201: JournalEntryDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company or entry not found"),
            409: OpenApiResponse(
                description="Already reversed, closed period, or read-only demo company"
            ),
        },
        tags=["journal"],
    )
    def post(self, request: Request, company_id: int, entry_id: int) -> Response:
        company = company_selectors.get_company(pk=company_id, user=request.user)
        original = selectors.get_journal_entry(pk=entry_id, company=company)

        serializer = JournalEntryReverseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reversal_entry = services.reverse_journal_entry(
            company=company,
            original_entry=original,
            created_by=request.user,
            date=serializer.validated_data.get("date"),
            description=serializer.validated_data.get("description", ""),
        )
        logger.info(
            "journal_entry_reversed",
            original_entry_id=original.pk,
            reversal_entry_id=reversal_entry.pk,
            company_id=company.pk,
            user=request.user.username,
        )
        entry_with_lines = selectors.get_journal_entry(pk=reversal_entry.pk, company=company)
        return Response(
            JournalEntryDetailSerializer(entry_with_lines).data, status=status.HTTP_201_CREATED
        )
