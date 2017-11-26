from django.contrib.auth import get_user_model, login, logout
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import DetailView, TemplateView, View

import tweepy

from .models import (TwitterProfile, TwitterRelationship, GENDER_CHOICES)
from .tasks import get_followers_and_friends
from .utils import get_tweepy_auth

User = get_user_model()


def get_ratio(counts):
    try:
        ratio = (
            (counts['male'] + counts['mostly_male']) /
            (counts['female'] + counts['mostly_female']))
    except ZeroDivisionError:
        ratio = 0
    return ratio


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
        context = super(
            BaseProfileView, self).get_context_data(*args, **kwargs)
        following_genders = list(
            TwitterRelationship.objects.filter(
                follower=self.object).values_list(
                'followed__gender', flat=True))
        following_counts = {g: following_genders.count(g) for g in
                            dict(GENDER_CHOICES).keys()}
        followers_genders = list(self.object.followed.values_list(
            'follower__gender', flat=True))
        followers_counts = {g: followers_genders.count(g) for g in
                            dict(GENDER_CHOICES).keys()}

        data = {'following_counts': following_counts,
                'followers_counts': followers_counts,
                'following_ratio': get_ratio(following_counts),
                'followers_ratio': get_ratio(followers_counts),
                }
        context.update(data)
        return context


class ProfileView(BaseProfileView):
    def post(self, request, *args, **kwargs):
        profile = self.get_object()
        if self.request.user.is_authenticated:
            get_followers_and_friends.delay(
                target_id=profile.id,
                authed_id=self.request.user.twitterprofile.id)
        return self.get(request, *args, **kwargs)


class ProfileCountsJSON(BaseProfileView):
    def render_to_response(self, context, **response_kwargs):
        data = {'profile': context['object'].serialized(),
                'following_counts': context['following_counts'],
                'followers_counts': context['followers_counts']}
        return JsonResponse(
            data,
            **response_kwargs
        )


class ProfileFollowingJSON(BaseProfileView):
    def render_to_response(self, context, **response_kwargs):
        following = TwitterRelationship.objects.filter(
            follower=self.object)
        id_idx = 1
        data = {'data': []}
        for rel in following:
            data['data'].append({
                'id': str(id_idx),
                'username': rel.followed.username,
                'name': rel.followed.show_data['name'],
                'gender': rel.followed.gender,
                'followers': str(rel.followed.show_data['followers_count']),
            })
            id_idx += 1
        return JsonResponse(
            data,
            **response_kwargs
        )


class ProfileFollowersJSON(BaseProfileView):
    def render_to_response(self, context, **response_kwargs):
        followers = self.object.followed.all()
        id_idx = 1
        data = {'data': []}
        for rel in followers:
            data['data'].append({
                'id': str(id_idx),
                'username': rel.follower.username,
                'name': rel.follower.show_data['name'],
                'gender': rel.follower.gender,
                'followers': str(rel.follower.show_data['followers_count']),
            })
            id_idx += 1
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
