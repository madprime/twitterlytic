from django.contrib.auth import get_user_model, login, logout
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, View

import tweepy

from .models import TwitterProfile
from .utils import get_tweepy_auth

User = get_user_model()


class HomeView(TemplateView):
    """
    Main page.
    """
    template_name = 'twitterlytic/index.html'

    def get_context_data(self, *args, **kwargs):
        context_data = super(HomeView, self).get_context_data(*args, **kwargs)

        auth = get_tweepy_auth()
        context_data['twitter_auth_url'] = auth.get_authorization_url()

        return context_data


class LogoutView(TemplateView):
    """
    Offer log out.
    """
    template_name = 'twitterlytic/logout.html'

    def post(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            logout(request)
        return HttpResponseRedirect(reverse_lazy('home'))


class TwitterReturnView(View):
    """
    Handle return from Twitter authentication.
    """

    def get(self, request, *args, **kwargs):

        # This is unexpected? Return home if already logged in.
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('home'))

        # Handle the Twitter return, get profile data.
        oauth_token = self.request.GET['oauth_token']
        oauth_verifier = self.request.GET['oauth_verifier']
        auth = get_tweepy_auth()
        auth.request_token = {'oauth_token': oauth_token,
                              'oauth_token_secret': oauth_verifier}
        (token, token_secret) = auth.get_access_token(oauth_verifier)
        auth.set_access_token(token, token_secret)
        api = tweepy.API(auth)
        user_data = api.me()

        # Get or create an account. Add core Twitter data.
        user, created = User.objects.get_or_create(
            username=user_data.screen_name)
        user.save()
        profile, _ = TwitterProfile.objects.get_or_create(
            username=user_data.screen_name, twitter_id=user_data.id)
        profile.oauth_token = token
        profile.oauth_token_secret = token_secret
        profile.user = user
        profile.save()

        # Log in user.
        user.backend = 'twitterlytic.backends.TrustedUserAuthenticationBackend'
        login(request, user)

        return HttpResponseRedirect(reverse_lazy('home'))
