from rest_framework import serializers

from apps.courses.models import Course, CourseEnrollment
from apps.journal.api.serializers import JournalEntryLineReadSerializer
from apps.journal.models import JournalEntry
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


class AvailableStudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name"]
        read_only_fields = fields

    def get_full_name(self, obj: User) -> str:
        return obj.get_full_name()


class EnrollmentCreateSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(min_value=1)

    def validate_student_id(self, value: int) -> int:
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Student not found.")
        return value


class TeacherCompanyItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    tax_id = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()


class TeacherStudentCompaniesSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_username = serializers.CharField()
    student_full_name = serializers.CharField(allow_blank=True)
    companies = TeacherCompanyItemSerializer(many=True)


class TeacherCourseCompaniesResponseSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    course_name = serializers.CharField()
    students = TeacherStudentCompaniesSerializer(many=True)


class TeacherCourseJournalEntrySerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    student_id = serializers.IntegerField(source="company.owner_id", read_only=True)
    student_username = serializers.CharField(source="company.owner.username", read_only=True)
    created_by = serializers.CharField(source="created_by.username", read_only=True)
    reversal_of_id = serializers.IntegerField(read_only=True)
    reversed_by_id = serializers.SerializerMethodField()
    lines = JournalEntryLineReadSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "entry_number",
            "date",
            "description",
            "source_type",
            "source_ref",
            "company_id",
            "company_name",
            "student_id",
            "student_username",
            "created_by",
            "reversal_of_id",
            "reversed_by_id",
            "lines",
        ]
        read_only_fields = fields

    def get_reversed_by_id(self, obj: JournalEntry) -> int | None:
        try:
            return obj.reversed_by.id
        except JournalEntry.reversed_by.RelatedObjectDoesNotExist:
            return None


class TeacherCourseJournalEntriesResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = TeacherCourseJournalEntrySerializer(many=True)


class AvailableStudentsPaginatedResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = AvailableStudentSerializer(many=True)
