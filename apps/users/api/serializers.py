from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Read serializer for the authenticated user."""

    role = serializers.CharField(read_only=True)
    course_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "role",
            "course_id",
            "date_joined",
        ]
        read_only_fields = fields

    def get_course_id(self, obj: User) -> int | None:
        if obj.role != User.Role.STUDENT:
            return None
        try:
            return obj.course_enrollment.course_id
        except ObjectDoesNotExist:
            return None


class UserUpdateSerializer(serializers.Serializer):
    """Write serializer for updating the authenticated user's profile."""

    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)
