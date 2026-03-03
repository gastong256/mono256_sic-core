from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Read serializer for the authenticated user."""

    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "role", "date_joined"]
        read_only_fields = ["id", "username", "email", "first_name", "last_name", "is_staff", "role", "date_joined"]

    def get_role(self, obj: User) -> str:
        return "teacher" if obj.is_staff else "student"


class UserUpdateSerializer(serializers.Serializer):
    """Write serializer for updating the authenticated user's profile."""

    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
