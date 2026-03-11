from django.urls import path

from apps.users.api.views import TeacherRegistrationCodeInfoView

app_name = "users-teacher"

urlpatterns = [
    path(
        "registration-code/",
        TeacherRegistrationCodeInfoView.as_view(),
        name="registration-code-info",
    ),
]
