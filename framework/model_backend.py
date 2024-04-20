from django.contrib.auth.backends import ModelBackend


class IsDeletedModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request=request, username=username, password=password, **kwargs)
        if user:
            if user.is_deleted:
                user = None
        return user
