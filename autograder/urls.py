# Django imports
from django.contrib import admin, auth
from django.urls import include, path
from django.views.generic import TemplateView

# Local imports
from .views import *
from .forms import StudentLoginForm

urlpatterns = [
	path('', Home.as_view(), name='home'),
    path('faq/', TemplateView.as_view(template_name='autograder/faq.html'), name='faq'),
    path('admin/', admin.site.urls),
    path('courses/', CourseListView.as_view(), name='course_list'),
    path('courses/create/', CourseCreateView.as_view(), name='create_course'),
    path('courses/<int:pk>/', CourseView.as_view(), name='view_course'),
    path('courses/<int:pk>/delete/', CourseDeleteView.as_view(), name='delete_course'),
    path('assignments/create/', AssignmentCreateView.as_view(), name='create_assignment'),
    path('assignments/<int:pk>/', AssignmentView.as_view(), name='view_assignment'),
    path('assignments/<int:pk>/delete/', AssignmentDeleteView.as_view(), name='delete_assignment'),
    path('assignments/<int:pk>/submissions', AssignmentSubmissionListView.as_view(), name='view_assignment_submissions'),
    path('test-cases/create/', TestCaseCreateView.as_view(), name='create_testcase'),
    path('test-cases/<int:pk>/', TestCaseView.as_view(), name='view_testcase'),
    path('test-cases/<int:pk>/delete/', TestCaseDeleteView.as_view(), name='delete_testcase'),
    path('assignments/<int:pk>/upload/', SubmissionCreateView.as_view(), name='create_submission'),
    path('submissions/<int:pk>/', SubmissionView.as_view(), name='view_submission'),
    path('submissions/<int:pk>/confirm/', SubmissionConfirmView.as_view(), name='confirm_submission'),
    path('submissions/<int:pk>/cancel/', SubmissionDeleteView.as_view(), name='delete_submission'),
    path('submissions/<int:pk>/download/', SubmissionDownloadView.as_view(), name='download_submission'),
    path('submissions/recent/', SubmissionRecentListView.as_view(), name='recent_submissions_list'),
    path('login/', auth.views.LoginView.as_view(template_name='autograder/student_login.html', authentication_form=StudentLoginForm), name='student_login'),
    path('logout/', auth.views.LogoutView.as_view(), name='logout'),
    path('staff-login/', auth.views.LoginView.as_view(template_name='autograder/staff_login.html'), name='staff_login'),
    path('students/', StudentListView.as_view(), name='list_students'),
    path('students/register/', StudentCreateView.as_view(), name='create_student'),
    path('students/register-bulk/', StudentBulkCreateView.as_view(), name='bulk_create_student'),
    path('students/<str:username>/', StudentView.as_view(), name='view_student'),
    path('students/<str:username>/delete', StudentDeleteView.as_view(), name='delete_student'),
    path('students/<str:username>/enroll', StudentEnrollView.as_view(), name='enroll_student'),
    path('students/<str:username>/unenroll', StudentUnenrollView.as_view(), name='unenroll_student')
]
