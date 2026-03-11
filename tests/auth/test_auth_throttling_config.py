from apps.users.api.auth_views import TokenObtainPairThrottledView, TokenRefreshThrottledView


def test_token_obtain_view_has_throttle_scope():
    assert TokenObtainPairThrottledView.throttle_scope == "auth_token_obtain"


def test_token_refresh_view_has_throttle_scope():
    assert TokenRefreshThrottledView.throttle_scope == "auth_token_refresh"
