from django.core.exceptions import ValidationError
from django.db import models

from apps.users.models import User


class TeacherAccountVisibility(models.Model):
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="account_visibility_overrides",
    )
    account = models.ForeignKey(
        "hordak.Account",
        on_delete=models.CASCADE,
        related_name="teacher_visibility_overrides",
    )
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("teacher", "account")]
        indexes = [
            models.Index(
                fields=["teacher", "is_visible", "account"],
                name="accounts_te_teacher_vis_ac_idx",
            ),
        ]

    def clean(self) -> None:
        if self.teacher.role != User.Role.TEACHER:
            raise ValidationError({"teacher": "Visibility overrides require a teacher user."})
        if self.account.level > 1:
            raise ValidationError(
                {"account": "Only level-0 and level-1 accounts support visibility overrides."}
            )

    def __str__(self) -> str:
        return f"{self.teacher.username} -> {self.account.full_code}: {self.is_visible}"
