import structlog
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors, services
from apps.accounts.api.permissions import IsAuthenticatedForAccounts
from apps.accounts.api.serializers import AccountCreateSerializer, AccountUpdateSerializer
from apps.companies import selectors as company_selectors

logger = structlog.get_logger(__name__)


class GlobalChartView(APIView):
    """Return the global chart of accounts (levels 1 and 2, no company-specific data)."""

    permission_classes = [IsAuthenticatedForAccounts]

    @extend_schema(
        operation_id="get_global_chart",
        summary="Get global chart of accounts",
        description=(
            "Returns the base chart of accounts (rubros and colectivas — levels 1 and 2). "
            "This is the shared, global plan with no company-specific subcuentas."
        ),
        responses={
            200: OpenApiResponse(description="Nested account tree (level 0 and 1)"),
            401: OpenApiResponse(description="Authentication required"),
        },
        tags=["accounts"],
    )
    def get(self, request: Request) -> Response:
        """Return the global chart of accounts as a nested tree."""
        tree = selectors.get_global_chart()
        return Response(tree)


class CompanyAccountListCreateView(APIView):
    """List all accounts for a company, or create a new level-3 account."""

    permission_classes = [IsAuthenticatedForAccounts]

    def _get_company(self, company_id: int, user):
        """Resolve the company, raising 404 or 403 as appropriate."""
        return company_selectors.get_company(pk=company_id, user=user)

    @extend_schema(
        operation_id="get_company_chart",
        summary="Get company chart of accounts",
        description=(
            "Returns the full chart of accounts for the given company: "
            "global levels 1 and 2, plus the company's own level-3 subcuentas."
        ),
        responses={
            200: OpenApiResponse(description="Nested account tree for the company"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company not found"),
        },
        tags=["accounts"],
    )
    def get(self, request: Request, company_id: int) -> Response:
        """Return the company's full chart of accounts as a nested tree."""
        company = self._get_company(company_id, request.user)
        tree = selectors.get_company_chart(company=company)
        return Response(tree)

    @extend_schema(
        operation_id="create_company_account",
        summary="Create a level-3 account for a company",
        description=(
            "Creates a new subcuenta (level-3 account) under the given colectiva (level-2 parent). "
            "Type and currency are inherited from the parent. "
            "Code must follow X.XX.XX format and be globally unique."
        ),
        request=AccountCreateSerializer,
        responses={
            201: OpenApiResponse(description="Created account node"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company or parent not found"),
        },
        tags=["accounts"],
    )
    def post(self, request: Request, company_id: int) -> Response:
        """Create a new level-3 account under the given company."""
        company = self._get_company(company_id, request.user)

        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = services.create_account(
            company=company,
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            parent_id=serializer.validated_data["parent_id"],
        )

        logger.info(
            "account_created",
            account_id=account.pk,
            company_id=company.pk,
            full_code=account.full_code,
            user=request.user.username,
        )

        from apps.accounts.selectors import _build_node

        return Response(_build_node(account), status=status.HTTP_201_CREATED)


class CompanyAccountDetailView(APIView):
    """Update or delete a single level-3 account belonging to a company."""

    permission_classes = [IsAuthenticatedForAccounts]

    def _get_account_and_company(self, company_id: int, account_id: int, user):
        """
        Resolve company and account, enforcing ownership.

        Returns (account, company) tuple.
        Raises 404 if the company or account is not found.
        Raises 403 if the user does not have access to the company.
        """
        from hordak.models import Account
        from rest_framework.exceptions import NotFound

        company = company_selectors.get_company(pk=company_id, user=user)

        try:
            account = Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            raise NotFound(detail="Account not found.")

        return account, company

    @extend_schema(
        operation_id="update_company_account",
        summary="Update a level-3 account",
        description="Update the name and/or code of a company-owned level-3 account.",
        request=AccountUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Updated account node"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company or account not found"),
        },
        tags=["accounts"],
    )
    def patch(self, request: Request, company_id: int, account_id: int) -> Response:
        """Partially update a level-3 account (name and/or code)."""
        account, company = self._get_account_and_company(company_id, account_id, request.user)

        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = services.update_account(
            account=account,
            company=company,
            name=serializer.validated_data.get("name"),
            code=serializer.validated_data.get("code"),
        )

        logger.info(
            "account_updated",
            account_id=account.pk,
            company_id=company.pk,
            user=request.user.username,
        )

        from apps.accounts.selectors import _build_node

        return Response(_build_node(account))

    @extend_schema(
        operation_id="delete_company_account",
        summary="Delete a level-3 account",
        description=(
            "Delete a company-owned level-3 account. "
            "Returns 409 Conflict if the account has existing transaction legs."
        ),
        responses={
            204: OpenApiResponse(description="No content"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not the company owner or teacher"),
            404: OpenApiResponse(description="Company or account not found"),
            409: OpenApiResponse(description="Account has existing transactions"),
        },
        tags=["accounts"],
    )
    def delete(self, request: Request, company_id: int, account_id: int) -> Response:
        """Delete a level-3 account (only if it has no transaction legs)."""
        account, company = self._get_account_and_company(company_id, account_id, request.user)

        services.delete_account(account=account, company=company)

        logger.info(
            "account_deleted",
            account_id=account_id,
            company_id=company.pk,
            user=request.user.username,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
