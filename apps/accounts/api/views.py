import structlog
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors, services
from apps.accounts.visibility import bump_teacher_visibility_cache_version
from apps.accounts.api.permissions import IsAuthenticatedForAccounts
from apps.accounts.api.serializers import (
    AccountCreateSerializer,
    AccountUpdateSerializer,
    AccountVisibilityUpdateSerializer,
)
from apps.common.role_resolution import resolve_teacher_for_actor
from apps.companies import selectors as company_selectors
from apps.users.models import User

logger = structlog.get_logger(__name__)


class GlobalChartView(APIView):
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
        tree = selectors.get_global_chart(user=request.user)
        return Response(tree)


class CompanyAccountListCreateView(APIView):
    permission_classes = [IsAuthenticatedForAccounts]

    def _get_company(self, company_id: int, user):
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
        company = self._get_company(company_id, request.user)
        tree = selectors.get_company_chart(company=company, user=request.user)
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
        company = self._get_company(company_id, request.user)

        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = services.create_account(
            company=company,
            actor=request.user,
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
    permission_classes = [IsAuthenticatedForAccounts]

    def _get_account_and_company(self, company_id: int, account_id: int, user):
        from apps.companies.models import CompanyAccount
        from rest_framework.exceptions import NotFound

        company = company_selectors.get_company(pk=company_id, user=user)

        try:
            company_account = CompanyAccount.objects.select_related("account").get(
                account_id=account_id,
                company=company,
            )
        except CompanyAccount.DoesNotExist:
            raise NotFound(detail="Account not found.")

        return company_account.account, company

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
        account, company = self._get_account_and_company(company_id, account_id, request.user)

        serializer = AccountUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        account = services.update_account(
            account=account,
            company=company,
            actor=request.user,
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
        account, company = self._get_account_and_company(company_id, account_id, request.user)

        services.delete_account(account=account, company=company)

        logger.info(
            "account_deleted",
            account_id=account_id,
            company_id=company.pk,
            user=request.user.username,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class _TeacherResolverMixin:
    def _resolve_teacher(self, request: Request) -> User:
        from rest_framework.exceptions import ValidationError

        teacher_id_raw = request.query_params.get("teacher_id") or request.data.get("teacher_id")
        if teacher_id_raw:
            try:
                teacher_id = int(teacher_id_raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError({"teacher_id": "teacher_id must be an integer."}) from exc
        else:
            teacher_id = None
        return resolve_teacher_for_actor(
            actor=request.user,
            teacher_id=teacher_id,
            missing_teacher_id_message="teacher_id is required for admin requests.",
        )


class TeacherAccountVisibilityListView(_TeacherResolverMixin, APIView):
    permission_classes = [IsAuthenticatedForAccounts]

    @extend_schema(
        operation_id="list_account_visibility_chart",
        summary="Get account visibility overrides",
        responses={200: OpenApiResponse(description="Level-0/1 tree with is_visible flags")},
        tags=["account-visibility"],
    )
    def get(self, request: Request) -> Response:
        teacher = self._resolve_teacher(request)
        return Response(selectors.get_teacher_visibility_chart(teacher=teacher))


class TeacherAccountVisibilityDetailView(_TeacherResolverMixin, APIView):
    permission_classes = [IsAuthenticatedForAccounts]

    @extend_schema(
        operation_id="update_account_visibility_override",
        summary="Set account visibility override",
        request=AccountVisibilityUpdateSerializer,
        responses={200: OpenApiResponse(description="Updated visibility tree")},
        tags=["account-visibility"],
    )
    def patch(self, request: Request, account_id: int) -> Response:
        from rest_framework.exceptions import ValidationError
        from apps.accounts.models import TeacherAccountVisibility
        from hordak.models import Account

        teacher = self._resolve_teacher(request)

        serializer = AccountVisibilityUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            account = Account.objects.get(pk=account_id)
        except Account.DoesNotExist:
            raise ValidationError({"account_id": "Account not found."})
        if account.level > 1:
            raise ValidationError({"account_id": "Only level-0/1 accounts can be hidden."})

        visibility, _ = TeacherAccountVisibility.objects.get_or_create(
            teacher=teacher,
            account=account,
            defaults={"is_visible": serializer.validated_data["is_visible"]},
        )
        visibility.is_visible = serializer.validated_data["is_visible"]
        visibility.full_clean()
        visibility.save(update_fields=["is_visible", "updated_at"])
        bump_teacher_visibility_cache_version(teacher_id=teacher.pk)

        logger.info(
            "account_visibility_updated",
            actor_id=request.user.pk,
            teacher_id=teacher.pk,
            account_id=account.pk,
            is_visible=visibility.is_visible,
        )
        return Response(selectors.get_teacher_visibility_chart(teacher=teacher))
