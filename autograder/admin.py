# Django imports
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group

# Local imports
from .forms import CourseAdminForm, StaffAdminForm, StudentAdminForm, SubmissionAdminForm, TestCaseCreateForm
from .models import *


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'course', 'pk')


@admin.register(AutograderUser)
class AutograderUserAdmin(admin.ModelAdmin):
    
    list_display = ('__str__', 'admin_gav_id_display', 'is_active')

    # Staff and Students have slightly different admin forms
    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = StaffAdminForm if obj.is_staff else StudentAdminForm
        return super().get_form(request, obj, **kwargs)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm


@admin.display(description='assignment')
def test_output_assignment_display(test_output):
    return test_output.submission.assignment

@admin.display(description='Student')
def test_output_student_display(test_output):
    student = test_output.submission.student
    return f'G00 {student.username} ({student})'

@admin.display(description='Submission PK')
def test_output_submission_pk_display(test_output):
    return test_output.submission.pk


@admin.register(TestOutput)
class TestOutputAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        test_output_assignment_display,
        test_output_student_display,
        test_output_submission_pk_display
    )


# A "Link" column for submissions, showing only the string "View" in every row
@admin.display(description='Link')
def submission_link_display(obj):
    return 'View'

@admin.display(description='Student')
def submission_student_display(submission):
    return f'G00 {submission.student.username} ({submission.student})'

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):

    form = SubmissionAdminForm
    list_display = (
        submission_link_display, 
        submission_student_display,
        'assignment',
        'date',
        'confirmed',
        'pk'
    )
    readonly_fields = ('compiles',)


@admin.display(description='Course')
def test_case_course_display(test_case):
    return test_case.assignment.course


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    # Use the same form as on the main site to ensure correct processing
    form = TestCaseCreateForm
    list_display = ('__str__', 'pk', 'assignment', test_case_course_display)


# Unregister Group model
admin.site.unregister(Group)
