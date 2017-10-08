from django.contrib.auth import get_user_model, login, logout
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import DetailView, TemplateView, View

import tweepy

from .models import TwitterProfile, TwitterRelationship, GENDER_CHOICES
from .celery import debug_task
from .tasks import get_followers_and_friends
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
        self.request.session['request_token'] = auth.request_token

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


class BaseProfileView(DetailView):
    """
    Twitter profile information.
    """
    template_name = 'twitterlytic/profile.html'
    model = TwitterProfile
    slug_field = 'username'

    def get_context_data(self, *args, **kwargs):
        print("IN HOME")
        context_data = super(
            BaseProfileView, self).get_context_data(*args, **kwargs)

        following = [rel.followed for rel in
                     TwitterRelationship.objects.filter(follower=self.object)]
        followers = [rel.follower for rel in
                     TwitterRelationship.objects.filter(followed=self.object)]

        following_counts = {k: 0 for k in dict(GENDER_CHOICES).keys()}
        followers_counts = {k: 0 for k in dict(GENDER_CHOICES).keys()}

        for profile in following:
            following_counts[profile.gender] += 1
        for profile in followers:
            followers_counts[profile.gender] += 1

        context_data.update({
            'following': following,
            'followers': followers,
            'following_counts': following_counts,
            'followers_counts': followers_counts,
        })

        return context_data


class ProfileView(BaseProfileView):
    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        if self.request.user.is_authenticated:
            get_followers_and_friends.delay(
                target_id=profile.id,
                authed_id=self.request.user.twitterprofile.id)
        return self.get(request, *args, **kwargs)


class ProfileViewJSON(BaseProfileView):
    def render_to_response(self, context, **response_kwargs):
        data = {'profile': context['object'].serialized(),
                'following_counts': context['following_counts'],
                'followers_counts': context['followers_counts']}
        return JsonResponse(
            data,
            **response_kwargs
        )


class TwitterReturnView(View):
    """
    Handle return from Twitter authentication.
    """

    def get(self, request, *args, **kwargs):
        print("IN TWITTER RETURN")

        # This is unexpected? Return home if already logged in.
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('home'))

        # Handle the Twitter return, get profile data.
        auth = get_tweepy_auth()
        request_token = self.request.session.pop('request_token')
        auth.request_token = request_token
        verifier = self.request.GET['oauth_verifier']

        (access_token, access_token_secret) = auth.get_access_token(verifier)
        print("GOT TOKENS")
        # auth.set_access_token(token, token_secret)
        api = tweepy.API(auth)
        user_data = api.me()
        print("GOT MY DATA")

        # Get or create an account. Add core Twitter data.
        user, created = User.objects.get_or_create(
            username=user_data.screen_name)
        user.save()
        print("MADE USER")
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=user_data.id)
        profile.username = user_data.screen_name
        profile.oauth_token = access_token
        profile.oauth_token_secret = access_token_secret
        profile.user = user
        profile.save()
        print("MADE PROFILE")
        import sys
        print(sys.version_info)
        print("CALLING EASY TASK")
        get_followers_and_friends.delay(
            target_id=profile.id,
            authed_id=profile.id)
        print("STARTED TASK")

        # Log in user.
        user.backend = 'twitterlytic.backends.TrustedUserAuthenticationBackend'
        login(request, user)
        print("LOGIN DONE")

        return HttpResponseRedirect(reverse_lazy('home'))
