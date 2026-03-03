from django.contrib import admin

from apps.courses.models import Course, CourseEnrollment


class CourseEnrollmentInline(admin.TabularInline):
    model = CourseEnrollment
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "teacher", "created_at")
    list_filter = ("teacher",)
    search_fields = ("name", "code", "teacher__username")
    inlines = [CourseEnrollmentInline]


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "course", "created_at")
    list_filter = ("course",)
    search_fields = ("student__username", "course__name", "course__code")
