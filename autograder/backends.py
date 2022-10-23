# Django imports
from django.contrib.auth.backends import ModelBackend

# Local imports
from .models import AutograderUser

class StudentBackend(ModelBackend):

    def authenticate(self, request, username=None):

        try:
            user = AutograderUser.objects.get(username=username)
        
        # Security fix copied from Django's source code, see Django ticket #20760
        except AutograderUser.DoesNotExist:
            AutograderUser().set_password(None)

        else:
            if self.user_can_authenticate(user):
                return user

    # Prevent this backend from authenticating staff accounts
    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and not user.is_staff
