# Standard imports
from datetime import datetime
import os
import shutil
import subprocess

# Django imports
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.dispatch.dispatcher import receiver
from django.urls import reverse_lazy

# Docker import
import docker


class AutograderUser(AbstractUser):

    def __str__(self):
        return self.get_full_name()

    @admin.display(description='Gav ID')
    def admin_gav_id_display(self):
        return f'G00 {self.username}' if not self.is_staff else None

    # Staff accounts = instructors
    # Non-staff accounts = students


class Course(models.Model):

    title = models.CharField(max_length=100)

    students = models.ManyToManyField(AutograderUser)

    def __str__(self):
        return self.title
    
    def build_absolute_url(self):
        return reverse_lazy('view_course', args=[self.id])
    

class Assignment(models.Model):

    title = models.CharField(max_length=280)

    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
    
    def build_absolute_url(self):
        return reverse_lazy('view_assignment', args=[self.id])
    
    def get_absolute_url(self):
        return self.build_absolute_url()


class TestCase(models.Model):

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)

    input = models.TextField(blank=True)
    output = models.TextField(blank=True)

    def __str__(self):
        return f'Test Case for {self.assignment.title}'

# When a test case is updated, delete its test outputs so tests are re-run with the updated test case
@receiver(models.signals.pre_save, sender=TestCase)
def delete_obsolete_testoutputs(sender, instance, **kwargs):

    # Not necessary when test case is created
    if instance._state.adding:
        return
    
    # NOTE: This will not call the delete() method of any TestOutput objects,
        #   so if TestOutput.delete() is overridden in the future, then change this.
    transaction.on_commit(lambda: TestOutput.objects.filter(testcase=instance).delete())


def submission_path(instance, filename):
    return os.path.join(
        'student-files',
        str(instance.student.username),
        str(instance.assignment.id),
        datetime.now().strftime('%Y-%m-%d-%H%M%S'),
        filename
    )


class Submission(models.Model):
    
    student = models.ForeignKey(AutograderUser, on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)

    date = models.DateTimeField(auto_now=True)
    confirmed = models.BooleanField(default=False)

    source_file = models.FileField(upload_to=submission_path)

    compiles = models.BooleanField(default=False)

    def __str__(self):
        return f'Submission from {self.student} for {self.assignment}'
    
    def build_absolute_url(self):
        return reverse_lazy('view_submission', args=[self.id])
    
    def get_absolute_url(self):
        return self.build_absolute_url()

    def build_download_url(self):
        return reverse_lazy('download_submission', args=[self.id])

    def get_context_path(self):
        return os.path.join(settings.MEDIA_ROOT, 'docker', f'context-{self.pk}')

    def docker_prep(self, client):

        # Create context directory, including intermediate directories if necessary
        context_path = self.get_context_path()
        os.makedirs(context_path)

        # Attempt to compile
        try:
            arg_list = ['g++', '-o', os.path.join(context_path, 'student-program'), self.source_file.path]
            subprocess.check_call(arg_list, timeout=2)
        except:
            # Destroy context if compilation fails
            shutil.rmtree(context_path)
            return None
        
        # Copy Dockerfile to context
        shutil.copy(os.path.join(settings.BASE_DIR, 'Dockerfile'), context_path)

        # Create input files in context
        for testcase in self.assignment.testcase_set.all():
            with open(os.path.join(context_path, f'input-file-{testcase.pk}.txt'), 'w') as input_file:
                input_file.write(testcase.input)

        # Build image
        image_tag = f'gav-autograder/submission-{self.pk}'
        client.images.build(path=context_path, tag=image_tag)

        return image_tag

    def full_test(self):

        # Remove old TestOutputs
        # NOTE: This will not call the delete() method of any TestOutput objects,
        #   so if TestOutput.delete() is overridden in the future, then change this.
        TestOutput.objects.filter(submission=self).delete()

        # Get docker client
        docker_client = docker.from_env()

        # Create docker context and image
        image_tag = self.docker_prep(docker_client)

        # Run tests if prep succeeded
        if image_tag is not None:
            
            for testcase in self.assignment.testcase_set.all():
                self.single_test(docker_client, image_tag, testcase)
        
            # Remove docker context and image
            self.docker_cleanup(docker_client, image_tag)

        return (image_tag is not None)

    def single_test(self, client, image_tag, testcase):

        # Create
        container = client.containers.create(
            image_tag,
            command=f'bash -c "./student-program < input-file-{testcase.pk}.txt"',
            cpu_shares=512,
            cpuset_cpus='0',
            mem_limit='500m',
            network_disabled=True,
            read_only=True,
            security_opt=['no-new-privileges'],
            version='auto'
        )
        # Start
        container.start()
        # Wait
        container.wait(timeout=5)
        # Get Logs
        container_output = container.logs().decode()
        # Remove
        container.remove()

        with open(os.path.join(settings.MEDIA_ROOT, 'log.txt'), 'a+') as log:
            log.write('Test output:\n')
            log.write(container_output)

        # Create TestOutput object
        TestOutput.objects.create(
            submission=self,
            testcase=testcase,
            output=container_output
        )

        return container_output

    def docker_cleanup(self, client, image_tag):
        
        # Remove image
        client.images.remove(image_tag)

        # Delete context directory
        shutil.rmtree(self.get_context_path())

    def save(self, *args, **kwargs):

        # Save normally, ensure source_file exists
        super().save(*args, **kwargs)

        # Unless otherwise specified, run all tests
        if kwargs.get('run_tests', True):

            # Set compiles flag if program compiles
            self.compiles = self.full_test()

            # Save changes
            super().save(update_fields=['compiles'])

    @property
    def test_results(self):

        results = {'compiles': self.compiles, 'tests': []}

        # No need to continue if program doesn't compile
        if not self._state.adding and not self.compiles:
            return results
        
        docker_client = None
        image_tag = None

        for testcase in self.assignment.testcase_set.all():

            try:
                test_output = self.testoutput_set.get(testcase=testcase).output
            
            except TestOutput.DoesNotExist:

                if docker_client is None:
                    docker_client = docker.from_env()
                    image_tag = self.docker_prep(docker_client)
                
                test_output = self.single_test(docker_client, image_tag, testcase)
            
            result = {
                # Required for calculating grade
                'passed': test_output == testcase.output,
                # Required for display on submission page
                'input': testcase.input,
                'output': [
                    {
                        'char': test_output[i],
                        'incorrect': (i >= len(testcase.output)) or (test_output[i] != testcase.output[i]),
                        'newline': (test_output[i] == '\n')
                    }
                    for i in range(len(test_output))
                ],
                'missing_output': len(testcase.output) - len(test_output)
            }
            
            results['tests'].append(result)
        
        if docker_client is not None:
            self.docker_cleanup(docker_client, image_tag)

        return results

    def delete_source_file_directory(self, directory):
        top_directory = os.path.join(settings.MEDIA_ROOT, 'student-files')
        # Ensure directory is empty before deleting it to prevent accidental deletions
        while directory != top_directory and not os.listdir(directory):
            os.rmdir(directory)
            directory = os.path.dirname(directory)

    # Deletes source_file and its parent directory, if empty
    def delete_source_file(self):
        path = self.source_file.path
        if os.path.exists(path):
            self.source_file.delete(False)
            self.delete_source_file_directory(os.path.dirname(path))

# When a submission's student, assignment, or source_file field is updated,
#   move/delete the old source_file
@receiver(models.signals.pre_save, sender=Submission, weak=False)
def move_or_delete_submission_file(sender, instance, **kwargs):

    if instance._state.adding or kwargs.get('update_fields', None) is None:
        return

    if 'source_file' in kwargs['update_fields']:

        # Retrieve old submission instance
        old_submission = Submission.objects.get(pk=instance.pk)

        # Delete old source file
        transaction.on_commit(lambda: old_submission.delete_source_file())

    elif 'student' in kwargs['update_fields'] or 'assignment' in kwargs['update_fields']:

        # Take note of old (absolute) path
        old_path = instance.source_file.path

        # Create new file name (and relative path)
        new_name = submission_path(instance, os.path.basename(old_path))

        def move_submission_file():

            # Set new file name on instance
            instance.source_file.name = new_name

            # Create actual (absolute) directories as necessary
            new_dir = os.path.join(settings.MEDIA_ROOT, os.path.dirname(new_name))
            os.makedirs(new_dir)

            # Move actual source file
            os.rename(old_path, os.path.join(new_dir, os.path.basename(new_name)))

            # Delete parent directory, if empty
            instance.delete_source_file_directory(os.path.dirname(old_path))

            # NOTE: instance does NOT need to be saved since this recieves a pre_save signal
        
        transaction.on_commit(move_submission_file)

# When a submission is deleted, delete its source_code file and parent directory as well
@receiver(models.signals.pre_delete, sender=Submission)
def delete_submission_file(sender, instance, **kwargs):
    transaction.on_commit(instance.delete_source_file)


class TestOutput(models.Model):

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE)

    output = models.TextField()

    def __str__(self):
        return f'Test output {self.pk}'
