from django.urls import path

from apps.users.api.views import UserRoleUpdateView

app_name = "users-admin"

urlpatterns = [
    path("users/<int:user_id>/role/", UserRoleUpdateView.as_view(), name="user-role-update"),
]
