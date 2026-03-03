from rest_framework import serializers

from apps.courses.models import Course, CourseEnrollment
from apps.users.models import User


class CourseSerializer(serializers.ModelSerializer):
    teacher_id = serializers.IntegerField(source="teacher.id", read_only=True)
    teacher_username = serializers.CharField(source="teacher.username", read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "code",
            "teacher_id",
            "teacher_username",
            "student_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_student_count(self, obj: Course) -> int:
        return obj.enrollments.count()


class CourseWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    teacher_id = serializers.IntegerField(required=False, min_value=1)


class EnrollmentSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ["student_id", "student_username", "created_at"]
        read_only_fields = fields


class EnrollmentCreateSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(min_value=1)

    def validate_student_id(self, value: int) -> int:
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Student not found.")
        return value
