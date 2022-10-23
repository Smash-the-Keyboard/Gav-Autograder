# Standard imports
from os import path
import datetime

# Django imports
from django import template

register = template.Library()

@register.filter
def filebasename(file):
    return path.basename(file.name)

@register.filter
def testcaseoutput(output):
    return output.replace('\n', '<span class="testcase-output-newline">\\n</span>\n')

@register.filter
def submissiongrade(submission):
    test_results = submission.test_results
    if test_results['compiles']:
        passed = len(list(filter(lambda result: result['passed'], test_results['tests'])))
        total = submission.assignment.testcase_set.count()
        percent = (passed / total) * 100
        return f'{percent:.2f}% ({passed}/{total})'
    else:
        return 'Compilation Failed or Timed Out'