import copy

from django.contrib.auth import get_user_model, login, logout
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import DetailView, TemplateView, View

import tweepy

from .models import TwitterProfile, TwitterRelationship, GENDER_COUNTS_BLANK
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
        context_data = super(
            BaseProfileView, self).get_context_data(*args, **kwargs)

        self.following = TwitterRelationship.objects.filter(follower=self.object)
        self.followers = self.object.followed.all()

        context_data.update({
            'following': self.following,
            'followers': self.followers,
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
        following_counts = copy.deepcopy(GENDER_COUNTS_BLANK)
        followers_counts = copy.deepcopy(GENDER_COUNTS_BLANK)

        for rel in self.following:
            following_counts[rel.followed.gender] += 1
        for rel in self.followers:
            followers_counts[rel.follower.gender] += 1

        data = {'profile': context['object'].serialized(),
                'following_counts': following_counts,
                'followers_counts': followers_counts}
        return JsonResponse(
            data,
            **response_kwargs
        )


class TwitterReturnView(View):
    """
    Handle return from Twitter authentication.
    """

    def get(self, request, *args, **kwargs):
        # This is unexpected? Return home if already logged in.
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy('home'))

        # Handle the Twitter return, get profile data.
        auth = get_tweepy_auth()
        request_token = self.request.session.pop('request_token')
        auth.request_token = request_token
        verifier = self.request.GET['oauth_verifier']

        (access_token, access_token_secret) = auth.get_access_token(verifier)
        # auth.set_access_token(token, token_secret)
        api = tweepy.API(auth)
        user_data = api.me()

        # Get or create an account. Add core Twitter data.
        user, created = User.objects.get_or_create(
            username=user_data.screen_name)
        user.save()
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=user_data.id)
        profile.oauth_token = access_token
        profile.oauth_token_secret = access_token_secret
        profile.user = user
        profile.save()
        get_followers_and_friends.delay(
            target_id=profile.id,
            authed_id=profile.id)

        # Log in user.
        user.backend = 'twitterlytic.backends.TrustedUserAuthenticationBackend'
        login(request, user)

        return HttpResponseRedirect(reverse_lazy('home'))
