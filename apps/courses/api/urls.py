from django.urls import path

from apps.courses.api.views import (
    CourseDetailView,
    CourseEnrollmentCreateView,
    CourseEnrollmentDeleteView,
    CourseDemoCompanyVisibilityDetailView,
    CourseDemoCompanyVisibilityListView,
    CourseSharedCompanyVisibilityDetailView,
    CourseSharedCompanyVisibilityListView,
    CourseListCreateView,
    TeacherAvailableStudentsView,
    TeacherCourseCompaniesView,
    TeacherCourseCompaniesSummaryView,
    TeacherCourseJournalEntriesAllView,
    TeacherCourseJournalEntriesView,
    TeacherCoursesOverviewView,
    TeacherStudentContextView,
)

app_name = "courses"

urlpatterns = [
    path("courses/", CourseListCreateView.as_view(), name="course-list-create"),
    path("courses/<int:course_id>/", CourseDetailView.as_view(), name="course-detail"),
    path(
        "courses/<int:course_id>/enrollments/",
        CourseEnrollmentCreateView.as_view(),
        name="course-enrollment-create",
    ),
    path(
        "courses/<int:course_id>/enrollments/<int:student_id>/",
        CourseEnrollmentDeleteView.as_view(),
        name="course-enrollment-delete",
    ),
    path(
        "courses/<int:course_id>/demo-companies/",
        CourseDemoCompanyVisibilityListView.as_view(),
        name="course-demo-company-list",
    ),
    path(
        "courses/<int:course_id>/demo-companies/<int:company_id>/",
        CourseDemoCompanyVisibilityDetailView.as_view(),
        name="course-demo-company-detail",
    ),
    path(
        "courses/<int:course_id>/shared-companies/",
        CourseSharedCompanyVisibilityListView.as_view(),
        name="course-shared-company-list",
    ),
    path(
        "courses/<int:course_id>/shared-companies/<int:company_id>/",
        CourseSharedCompanyVisibilityDetailView.as_view(),
        name="course-shared-company-detail",
    ),
    path(
        "teacher/courses/<int:course_id>/companies/",
        TeacherCourseCompaniesView.as_view(),
        name="teacher-course-companies",
    ),
    path(
        "teacher/courses/overview/",
        TeacherCoursesOverviewView.as_view(),
        name="teacher-courses-overview",
    ),
    path(
        "teacher/courses/<int:course_id>/companies/summary/",
        TeacherCourseCompaniesSummaryView.as_view(),
        name="teacher-course-companies-summary",
    ),
    path(
        "teacher/courses/<int:course_id>/journal-entries/",
        TeacherCourseJournalEntriesView.as_view(),
        name="teacher-course-journal-entries",
    ),
    path(
        "teacher/courses/<int:course_id>/journal-entries/all/",
        TeacherCourseJournalEntriesAllView.as_view(),
        name="teacher-course-journal-entries-all",
    ),
    path(
        "teacher/students/available/",
        TeacherAvailableStudentsView.as_view(),
        name="teacher-available-students",
    ),
    path(
        "teacher/students/<int:student_id>/context/",
        TeacherStudentContextView.as_view(),
        name="teacher-student-context",
    ),
]
