from django.urls import path

from apps.users.api.views import UserListView, UserRoleUpdateView

app_name = "users-admin"

urlpatterns = [
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:user_id>/role/", UserRoleUpdateView.as_view(), name="user-role-update"),
]
