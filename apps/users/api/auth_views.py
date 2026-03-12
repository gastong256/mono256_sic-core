from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class StableTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Keep refresh response contract stable for clients:
    always include a `refresh` token in the payload.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data["refresh"] = data.get("refresh") or attrs.get("refresh", "")
        return data


class TokenObtainPairThrottledView(TokenObtainPairView):
    throttle_scope = "auth_token_obtain"


class TokenRefreshThrottledView(TokenRefreshView):
    throttle_scope = "auth_token_refresh"
    serializer_class = StableTokenRefreshSerializer
