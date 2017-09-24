from django.contrib.auth.backends import ModelBackend


class TrustedUserAuthenticationBackend(ModelBackend):
    """
    Authenticate a trusted user. (No credentials checked.)
    """

    def authenticate(self, **credentials):
        return None
