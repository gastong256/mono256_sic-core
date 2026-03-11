from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class TokenObtainPairThrottledView(TokenObtainPairView):
    throttle_scope = "auth_token_obtain"


class TokenRefreshThrottledView(TokenRefreshView):
    throttle_scope = "auth_token_refresh"
