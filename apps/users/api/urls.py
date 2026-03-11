from django.urls import path

from apps.users.api.auth_views import TokenObtainPairThrottledView, TokenRefreshThrottledView
from apps.users.api.views import MeView, RegisterView

app_name = "users"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairThrottledView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshThrottledView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
