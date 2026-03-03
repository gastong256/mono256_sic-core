from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
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
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class UserRoleUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices)


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    registration_code = serializers.CharField(max_length=32)


class RegistrationCodeInfoSerializer(serializers.Serializer):
    code = serializers.CharField()
    window_minutes = serializers.IntegerField()
    allow_previous_window = serializers.BooleanField()
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField()


class UserListPaginatedSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = UserSerializer(many=True)
