# Standard imports
import csv
from io import StringIO

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, AccessMixin
from django.db import IntegrityError
from django.db.models import Count
from django.http import Http404, FileResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import View, DetailView, ListView
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView, FormView

# Local imports
from .forms import *
from .models import *

def log(msg):
	from django.conf import settings
	from os.path import join
	with open(join(settings.MEDIA_ROOT, 'views-log.txt'), 'a+') as f:
		f.write(msg + '\n')

class Home(TemplateView):
	template_name = 'autograder/index.html'


class CourseListView(ListView):
	model = Course


class CourseCreateView(PermissionRequiredMixin, CreateView):
	model = Course
	fields = ['title']
	permission_required = 'autograder.create_course'
	template_name_suffix = '_create'
	raise_exception = True

	def get_success_url(self):
		return self.object.build_absolute_url()


class CourseView(LoginRequiredMixin, DetailView):

	model = Course
	template_name_suffix = ''

	# Exclude assignments with no test cases from students' view
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['assignment_set'] = self.object.assignment_set.all()
		if not self.request.user.is_staff:
			context['assignment_set'] = self.object.assignment_set.annotate(Count('testcase')).exclude(testcase__count=0)
		return context

	def get(self, *args, **kwargs):
		response = super().get(*args, **kwargs)

		# Redirect unauthorized users
		if not self.request.user.is_staff and not self.object.students.filter(pk=self.request.user.id).exists():
			messages.warning(self.request, f'You are not enrolled in {self.object}')
			return HttpResponseRedirect(reverse('course_list'))

		return response


class CourseDeleteView(PermissionRequiredMixin, DeleteView):
	model = Course
	permission_required = 'autograder.delete_course'
	template_name_suffix = '_delete'
	success_url = reverse_lazy('course_list')
	raise_exception = True


class AssignmentCreateView(PermissionRequiredMixin, CreateView):
	model = Assignment
	form_class = AssignmentCreateForm
	permission_required = 'autograder.create_assignment'
	template_name_suffix = '_create'
	raise_exception = True

	# When creating an assignment, the course should default to the one in the url
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.get_form_class()
		form = form_class(**self.get_form_kwargs())
		course_id = self.request.GET.get('course')		
		if course_id is not None:
			course = Course.objects.filter(id=int(course_id))
			if course.exists():
				form.fields['course'].initial = course[0]
		return form

	def get_success_url(self):
		return self.object.build_absolute_url()


class AssignmentView(LoginRequiredMixin, DetailView):

	model = Assignment
	template_name_suffix = ''

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		# Retrieve current student's submissions and order by most recent
		user_submissions = self.request.user.submission_set.filter(assignment_id=self.object.pk).order_by('-date')
		context.update({
			'user_submissions': user_submissions,
			'user_has_unconfirmed_submission': user_submissions.filter(confirmed=False).exists()
		})
		return context

	def get(self, *args, **kwargs):
		response = super().get(*args, **kwargs)

		# Redirect unauthorized users
		if not self.request.user.is_staff and not self.object.course.students.filter(pk=self.request.user.id).exists():
			messages.warning(self.request, f'You are not enrolled in {self.object.course}')
			return HttpResponseRedirect(reverse('course_list'))
		
		# Deny students if assignment has no test cases
		if not self.request.user.is_staff and self.object.testcase_set.count() == 0:
			self.handle_no_permission()

		return response


class AssignmentDeleteView(PermissionRequiredMixin, DeleteView):
	model = Assignment
	permission_required = 'autograder.delete_assignment'
	template_name_suffix = '_delete'
	raise_exception = True
	
	def get_success_url(self):
		return self.object.course.build_absolute_url()


class AssignmentSubmissionListView(UserPassesTestMixin, ListView):

	model = Submission
	raise_exception = True

	def test_func(self):
		return self.request.user.is_staff
	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['assignment'] = self.assignment
		return context

	def get_queryset(self):

		assignment_pk = self.kwargs.get('pk')

		try:
			self.assignment = Assignment.objects.get(pk=assignment_pk)
		except Assignment.DoesNotExist:
			raise Http404(f'No Assignment found with id {assignment_pk}')

		return self.assignment.submission_set.all().order_by('-date')


class TestCaseCreateView(PermissionRequiredMixin, CreateView):
	model = TestCase
	form_class = TestCaseCreateForm
	permission_required = 'autograder.create_testcase'
	template_name_suffix = '_create'
	raise_exception = True

	# Set initial values and querysets for assignment field
	def get_form(self, form_class=None):
		if form_class is None:
			form_class = self.get_form_class()
		form = form_class(**self.get_form_kwargs())
		assignment_id = self.request.GET.get('assignment')		
		if assignment_id is not None:
			assignment = Assignment.objects.filter(id=int(assignment_id))
			if assignment.exists():
				assignment = assignment[0]
				form.fields['assignment'].initial = assignment
				form.fields['assignment'].queryset = assignment.course.assignment_set
		return form

	def get_success_url(self):
		return reverse('view_testcase', args=[self.object.pk])


class TestCaseView(LoginRequiredMixin, DetailView):

	model = TestCase
	template_name_suffix = ''

	def get(self, *args, **kwargs):
		response = super().get(*args, **kwargs)

		# Redirect unauthorized users
		if not self.request.user.is_staff and not self.object.assignment.course.students.filter(pk=self.request.user.id).exists():
			messages.warning(self.request, f'You are not enrolled in {self.object.assignment.course}')
			return HttpResponseRedirect(reverse('course_list'))

		return response


class TestCaseDeleteView(PermissionRequiredMixin, DeleteView):
	model = TestCase
	permission_required = 'autograder.delete_testcase'
	template_name_suffix = '_delete'
	raise_exception = True
	
	def get_success_url(self):
		return self.object.assignment.build_absolute_url()


class SubmissionCreateView(AccessMixin, CreateView):

	model = Submission
	template_name_suffix = '_upload'
	form_class = SubmissionCreateForm

	def dispatch(self, request, *args, **kwargs):

		# unauthenticated -> redirect to login
		if not request.user.is_authenticated:
			return self.handle_no_permission()
		
		self.assignment = Assignment.objects.get(pk=self.kwargs.get('pk'))

		# is staff -> redirect to assignment page with warning
		if request.user.is_staff:
			messages.warning(self.request, 'Please use the admin menu to create submissions')
			return HttpResponseRedirect(reverse('view_assignment', args=[self.assignment.pk]))

		# not course member -> redirect to course list with warning
		if not self.assignment.course.students.filter(pk=self.request.user.pk).exists():
			messages.warning(self.request, f'You are not enrolled in {self.assignment.course}')
			return HttpResponseRedirect(reverse('course_list'))

		# assignment has no test cases -> deny
		if self.assignment.testcase_set.count() == 0:
			self.handle_no_permission()

		# unconfirmed submission exists -> redirect to assignment page with error
		if request.user.submission_set.filter(assignment_id=self.assignment.pk, confirmed=False).exists():
			messages.error(self.request, 'You have an unconfirmed submission for this assignment. Confirm or cancel it before making another submission.')
			return HttpResponseRedirect(reverse('view_assignment', args=[self.assignment.pk]))

		# exceeded submission limit -> redirect to assignment page with error
		if request.user.submission_set.filter(assignment_id=self.assignment.pk).count() >= 10:
			messages.error(self.request, 'You have reached the maximum number of submissions permitted for this assignment.')
			return HttpResponseRedirect(reverse('view_assignment', args=[self.assignment.pk]))

		return super().dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		# Add assignment to context data so the page can link to it
		context.update({'assignment': self.assignment})
		return context

	def form_valid(self, form):
		# Set student to the current user
		form.instance.student = self.request.user
		# Set assignment from url parameter
		form.instance.assignment = self.assignment
		return super().form_valid(form)

	def get_success_url(self):
		return self.object.build_absolute_url()
	
	
class SubmissionView(LoginRequiredMixin, DetailView):

	model = Submission
	template_name_suffix = ''
	raise_exception = True

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update({
			'test_results': self.object.test_results,
			'source_file_contents': self.object.source_file.read().decode('utf-8')
		})
		return context

	def get(self, *args, **kwargs):
		response = super().get(*args, **kwargs)
		# Deny unauthorized users
		is_owner = (self.object.student.pk == self.request.user.pk)
		is_enrolled = (self.object.assignment.course.students.filter(pk=self.request.user.pk).exists())
		if not self.request.user.is_staff and (not is_owner or not is_enrolled):
			self.handle_no_permission()
		return response


class SubmissionConfirmView(AccessMixin, UpdateView):

	model = Submission
	template_name_suffix = '_confirm'
	raise_exception = True
	form_class = SubmissionConfirmForm

	def dispatch(self, request, *args, **kwargs):

		self.object = self.get_object()

		# Deny unauthenticated users
		if not request.user.is_authenticated:
			return self.handle_no_permission()
		# Redirect & tell staff to use admin menu to edit/delete submissions
		if request.user.is_staff:
			messages.warning(request, 'Please use the admin menu to edit/delete submissions')
			return HttpResponseRedirect(reverse('view_submission', args=[self.object.pk]))
		# Deny unauthorized users
		elif self.object.student.pk != request.user.pk or self.object.confirmed:
			self.handle_no_permission()
		
		return super().dispatch(request, *args, **kwargs)

	def get_success_url(self):
		return self.object.get_absolute_url()


class SubmissionDeleteView(AccessMixin, DeleteView):

	model = Submission
	template_name_suffix = '_cancel'
	raise_exception = True

	def dispatch(self, request, *args, **kwargs):

		self.object = self.get_object()

		# Deny unauthenticated users
		if not request.user.is_authenticated:
			self.handle_no_permission()
		# Redirect & tell staff to use admin menu to edit/delete submissions
		if request.user.is_staff:
			messages.warning(request, 'Please use the admin menu to edit/delete submissions')
			return HttpResponseRedirect(reverse('view_submission', args=[self.object.pk]))
		# Deny unauthorized users
		elif self.object.student.pk != request.user.pk or self.object.confirmed:
			self.handle_no_permission()

		return super().dispatch(request, *args, **kwargs)

	def get_success_url(self):
		return self.object.assignment.get_absolute_url()


class SubmissionDownloadView(LoginRequiredMixin, View):

	raise_exception = True

	def get(self, request, **kwargs):

		submission_pk = self.kwargs['pk']

		try:
			submission = Submission.objects.get(pk=submission_pk)
		except Submission.DoesNotExist:
			raise Http404(f'No Submission found with id {submission_pk}')

		if not request.user.is_staff and submission.student.pk != request.user.pk:
			self.handle_no_permission()

		return FileResponse(submission.source_file.open(mode='rb'), as_attachment=True)


class SubmissionRecentListView(UserPassesTestMixin, ListView):

	model = Submission
	raise_exception = True
	template_name_suffix = '_recent_list'

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		# Retrieve 10 most recent submissions, confirmed or otherwise
		return Submission.objects.all().order_by('-date')[:10]


class StudentListView(UserPassesTestMixin, ListView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student_list.html'

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		return AutograderUser.objects.filter(is_staff=False)


class StudentCreateView(UserPassesTestMixin, CreateView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student_register.html'
	form_class = StudentCreateForm

	def test_func(self):
		return self.request.user.is_staff

	def get_success_url(self):
		return reverse('view_student', args=[self.object.username])


class StudentBulkCreateView(UserPassesTestMixin, FormView):

	raise_exception = True
	template_name = 'autograder/student_register_bulk.html'
	success_url = reverse_lazy('list_students')
	form_class = StudentBulkCreateForm

	def test_func(self):
		return self.request.user.is_staff
	
	def form_valid(self, form):
		form_file = self.request.FILES['file']
		field_names = ['gav_id', 'first_name', 'last_name']
		if not form_file.multiple_chunks():
			csv_file = StringIO(form_file.read().decode('utf-8'))
			reader = csv.DictReader(csv_file, field_names)
			duplicates = {}
			for line in reader:
				try:
					student = AutograderUser.objects.create_user(line['gav_id'])
					student.first_name = line['first_name']
					student.last_name = line['last_name']
					student.save()
				except IntegrityError:
					duplicates[line['gav_id']] = duplicates.get(line['gav_id'], 0) + 1

			for dup_id in duplicates:
				messages.error(self.request, f'{duplicates[dup_id]} students with gav id {dup_id} were not created because a student with that id already exists')

		return super().form_valid(form)
	

class StudentView(UserPassesTestMixin, DetailView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student.html'

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		return AutograderUser.objects.filter(is_staff=False)

	# Include total number of courses so the template knows whether to show the "enroll" link or not
	# Also include this student's submissions
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['total_courses'] = Course.objects.count()
		context['submissions'] = self.object.submission_set.all().order_by('-date')
		return context

	def get_object(self):

		student_id = self.kwargs.get('username')

		try:
			student = self.get_queryset().get(username=student_id)
		except AutograderUser.DoesNotExist:
			raise Http404(f'No student found with student id {student_id}')
		
		return student


class StudentDeleteView(UserPassesTestMixin, DeleteView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student_delete.html'

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		return AutograderUser.objects.filter(is_staff=False)

	def get_object(self):

		student_id = self.kwargs.get('username')

		try:
			student = self.get_queryset().get(username=student_id)
		except AutograderUser.DoesNotExist:
			raise Http404(f'No student found with student id {student_id}')
		
		return student
	
	def get_success_url(self):
		return reverse('list_students')


class StudentEnrollView(UserPassesTestMixin, UpdateView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student_enroll.html'
	form_class = StudentEnrollmentForm

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		return AutograderUser.objects.filter(is_staff=False)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		# Exclude courses of which this student is already a member
		# Note that query.difference() cannot be used because Django doesn't fully support MariaDB
		kwargs.update({'courses_queryset': Course.objects.all().exclude(pk__in=self.object.course_set.all().values('pk'))})
		return kwargs

	def get_object(self):

		student_id = self.kwargs.get('username')

		try:
			student = self.get_queryset().get(username=student_id)
		except AutograderUser.DoesNotExist:
			raise Http404(f'No student found with student id {student_id}')
		
		return student

	def form_valid(self, form):
		self.object = self.get_object()
		for course in form.cleaned_data['courses']:
			course.students.add(self.object)
			course.save()
		return super().form_valid(form)

	def get_success_url(self):
		return reverse('view_student', args=[self.object.username])


class StudentUnenrollView(UserPassesTestMixin, UpdateView):

	model = AutograderUser
	raise_exception = True
	template_name = 'autograder/student_unenroll.html'
	form_class = StudentEnrollmentForm

	def test_func(self):
		return self.request.user.is_staff

	def get_queryset(self):
		return AutograderUser.objects.filter(is_staff=False)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		# Include only courses of which this student is already a member
		kwargs.update({'courses_queryset': self.object.course_set.all()})
		return kwargs

	def get_object(self):

		student_id = self.kwargs.get('username')

		try:
			student = self.get_queryset().get(username=student_id)
		except AutograderUser.DoesNotExist:
			raise Http404(f'No student found with student id {student_id}')
		
		return student

	# Redirect user if student has no classes from which to unenroll
	def get(self, request, *args, **kwargs):
		normal_response = super().get(request, *args, **kwargs)
		if self.object.course_set.all().count() == 0:
			messages.warning(self.request, 'This student has no courses to be unenrolled from')
			return HttpResponseRedirect(reverse('view_student', args=[self.object.username]))
		else:
			return normal_response

	def form_valid(self, form):
		self.object = self.get_object()
		for course in form.cleaned_data['courses']:
			course.students.remove(self.object)
			course.save()
		return super().form_valid(form)

	def get_success_url(self):
		return reverse('view_student', args=[self.object.username])
