# Django imports
from django import forms
from django.contrib.auth.forms import authenticate, AuthenticationForm
from django.utils.translation import gettext_lazy as _

# Local imports
from .models import Assignment, AutograderUser, Course, Submission, TestCase


class StudentLoginForm(AuthenticationForm):

    username = forms.CharField(label='Gavilan ID')
    password = None

    error_messages = {
        'invalid_login': _('Please enter a valid ID.'),
        'inactive': _('This account is inactive.')
    }

    def clean(self):

        username = self.cleaned_data.get('username')

        if username is not None:
            self.user_cache = authenticate(self.request, username=username)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class AssignmentCreateForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].help_text = 'Maximum 280 characters'
        self.fields['title'].widget.attrs.update(size='40')


class SubmissionCreateForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('source_file',)


class SubmissionConfirmForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ()
        
    def save(self, commit=True):
        # NOTE: Not sure why super().save() is called here instead of just accessing self.instance
        submission = super().save(commit=False)
        submission.confirmed = True
        # Only save confirmed field, since it's the only one changed by this form
        submission.save(update_fields=['confirmed'])
        return submission


class TestCaseCreateForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = '__all__'
    
    # Do NOT strip leading/trailing whitespace
    input = forms.CharField(widget=forms.Textarea(), strip=False, required=False)
    output = forms.CharField(widget=forms.Textarea(), strip=False, required=False)

    # Replace Windows line endings with Unix line endings
    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['input'] = cleaned_data.get('input').replace('\r\n', '\n')
        cleaned_data['output'] = cleaned_data.get('output').replace('\r\n', '\n')
        return cleaned_data


class StudentCreateForm(forms.ModelForm):
    class Meta:
        model = AutograderUser
        fields = ('username', 'first_name', 'last_name')
        labels = {'username': 'Gavilan ID'}
        help_texts = {'username': None}
        error_messages = {'username': {'unique': 'A student with that ID already exists.'}}


class StudentBulkCreateForm(forms.Form):
    file = forms.FileField(
        label='CSV File',
        widget=forms.FileInput(attrs={'accept':'text/csv'}),
        help_text='(Maximum 2.5 MB)'
    )


class StudentEnrollmentForm(forms.ModelForm):
    
    class Meta:
        model = AutograderUser
        fields = []

    courses = forms.ModelMultipleChoiceField(queryset=Course.objects.all(), widget=forms.CheckboxSelectMultiple())

    # Queryset for courses field may be specified as a keyword argument
    def __init__(self, *args, **kwargs):
        courses_queryset = kwargs.pop('courses_queryset', None)
        super().__init__(*args, **kwargs)
        if courses_queryset is not None:
            self.fields['courses'].queryset = courses_queryset


class StudentAdminForm(forms.ModelForm):

    username = forms.CharField(
        max_length=6,
        min_length=6,
        label='Gavilan ID',
        help_text='Required. 6 characters, numeric only.'
    )

    class Meta:
        model = AutograderUser
        exclude = ('password', 'is_superuser', 'groups', 'user_permissions', 'email')


class StaffAdminForm(forms.ModelForm):
    class Meta:
        model = AutograderUser
        exclude = ('is_superuser', 'groups', 'user_permissions', 'email')


# Custom ModelChoiceField that displays both student names and Gav IDs in the drop-down list
class StudentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'G00 {obj.username} - {obj}'


class SubmissionAdminForm(forms.ModelForm):

    class Meta:
        model = Submission
        fields = '__all__'
    
    # Queryset is set per-instance
    student = StudentChoiceField(queryset=None)

    # Limit choices for the student field to non-staff course members only
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = AutograderUser.objects.filter(is_staff=False, course=self.instance.assignment.course)

    def save(self, commit=True):

        # Save only modified fields during updates (but not when creating)
        if not self.instance._state.adding and self.changed_data:
            
            # First, save without committing to check for validation errors
            super().save(commit=False)
            
            # Pass changed_data to update_fields kwarg so changes to source_file can be handled
            self.instance.save(update_fields=self.changed_data)

            return self.instance
        
        return super().save(commit)


# Similar to StudentChoiceField
class StudentMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f'G00 {obj.username} - {obj}'


class CourseAdminForm(forms.ModelForm):

    class Meta:
        model = Course
        fields = '__all__'

    students = StudentMultipleChoiceField(
        queryset=AutograderUser.objects.filter(is_staff=False)
    )
    