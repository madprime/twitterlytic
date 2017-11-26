from datetime import timedelta
import json
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.utils import timezone

import gender_guesser.detector as gender
import requests
from requests_oauthlib import OAuth1
import tweepy

from .utils import get_tweepy_auth, RateExceededError

User = get_user_model()
gender_guesser = gender.Detector()

GENDER_CHOICES = (
    ('unknown', 'Unknown'),
    ('andy', 'Ambig/Neutral'),
    ('male', 'Male'),
    ('female', 'Female'),
    ('mostly_male', 'Likely male'),
    ('mostly_female', 'Likely female'),
)

GENDER_COUNTS_BLANK = {k: 0 for k in dict(GENDER_CHOICES).keys()}

SHOW_DATA_LIST = [
    'id', 'id_str', 'name', 'screen_name', 'location', 'url', 'description',
    'protected', 'verified', 'followers_count', 'friends_count',
    'listed_count', 'favourites_count', 'statuses_count', 'created_at',
    'utc_offset', 'time_zone', 'geo_enabled', 'lang',
    'profile_background_color', 'profile_background_image_url',
    'profile_background_image_url_https', 'profile_background_tile',
    'profile_banner_url', 'profile_image_url', 'profile_image_url_https',
    'profile_link_color', 'profile_sidebar_border_color',
    'profile_sidebar_fill_color', 'profile_text_color',
    'profile_use_background_image', 'default_profile', 'default_profile_image',
    'withheld_in_countries', 'withheld_scope',
]

TWITTER_CAPS = {
    'followers/ids.json': 15,
    'friends/ids.json': 15,
    'users/show.json': 900,
    'users/lookup.json': 900,
}


def guess_gender(name, description):
    if 'she/her' in description.lower():
        return 'female'
    elif 'he/him' in description.lower():
        return 'male'
    elif 'they/them' in description.lower():
        return 'andy'
    if name and name.split()[0].lower() == 'the':
        return 'unknown'
    try:
        return gender_guesser.get_gender(name.split()[0].title())
    except IndexError:
        return 'unknown'


def pick_authorizer(querent, path):
    query_window_start = timezone.now() - timedelta(minutes=15)
    choice_attempts = 0
    authed_profiles = TwitterProfile.objects.exclude(oauth_token='')
    while choice_attempts < 15:
        if choice_attempts == 0:
            authorizer = querent
        else:
            random_index = randint(0, authed_profiles.count() - 1)
            authorizer = authed_profiles[random_index]
        count = TwitterQuery.objects.filter(authorizer=authorizer).filter(
            timestamp__gt=query_window_start).filter(
            path=path).count()
        cap = 15 if path not in TWITTER_CAPS else TWITTER_CAPS[path]
        if authorizer.id != querent.id:
            cap = int(0.5 * cap)
        if count < cap:
            return authorizer
        print('ROUND {} fail :: For {} {}, tried {}. {} / {}'.format(
            choice_attempts, querent, path, authorizer, authorizer.id,
            count, cap))
        choice_attempts += 1


class TwitterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    twitter_id = models.BigIntegerField(unique=True)

    oauth_token = models.CharField(max_length=50, blank=True)
    oauth_token_secret = models.CharField(max_length=45, blank=True)

    show_data = JSONField(default={})
    username = models.CharField(max_length=20)
    gender = models.CharField(
        max_length=13,
        choices=GENDER_CHOICES,
        default='unknown',
    )
    last_show_refresh = models.DateTimeField(null=True)

    friends_ids = ArrayField(models.BigIntegerField(), null=True)
    followers_ids = ArrayField(models.BigIntegerField(), null=True)
    followers = models.ManyToManyField(
        'self', through='TwitterRelationship', symmetrical=False,
        through_fields=('followed', 'follower'),)
    friends_ratio = models.FloatField(null=True)
    followers_ratio = models.FloatField(null=True)
    last_full_refresh = models.DateTimeField(null=True)

    def __str__(self):
        return(self.username)

    def serialized(self):
        return {
            'twitter_id': self.twitter_id,
            'username': self.username,
            'name': self.show_data['name'],
            'description': self.show_data['description'],
            'gender': self.gender,
        }

    def get_auth(self):
        return OAuth1(
            settings.TWITTER_CONSUMER_TOKEN,
            settings.TWITTER_CONSUMER_SECRET,
            self.oauth_token,
            self.oauth_token_secret,)

    def api_call(self, path, params={}):
        authorizer = pick_authorizer(self, path)
        if not authorizer:
            raise RateExceededError
        req = requests.get(
            'https://api.twitter.com/1.1/' + path,
            params=params,
            auth=authorizer.get_auth())
        if req.status_code != 200:
            if 'errors' in req.json():
                for error in req.json()['errors']:
                    if error['code'] == 88:
                        raise RateExceededError
                    if error['code'] == 89:
                        authorizer.oauth_token = ''
                        authorizer.oauth_token_secret = ''
                        authorizer.save()
                        return self.api_call(path, params=params)
            print("Error for {} req: {}".format(
                authorizer.username, json.dumps(req.json())))
            raise Exception
        query = TwitterQuery(querent=self, authorizer=authorizer, path=path,
                             params=params)
        query.save()
        return req

    def refresh_show_data(self, auth_profile, data=None, max_sec_stale=0):
        if self.last_show_refresh:
            delta = timezone.now() - self.last_show_refresh
            if delta.seconds <= max_sec_stale:
                return
        if not data:
            req = auth_profile.api_call(
                path='users/show.json',
                params={'user_id': self.twitter_id},
                )
            data = req.json()
        results = {k: data[k] for k in data.keys() if k in SHOW_DATA_LIST}
        self.show_data = results
        self.username = self.show_data['screen_name']
        self.gender = guess_gender(self.show_data['name'],
                                   self.show_data['description'])
        self.last_show_refresh = timezone.now()
        self.save()

    def update_ids(self, ids_type, auth_profile):
        assert ids_type in ['friends', 'followers']
        ids = []
        done = False
        cursor = -1
        while not done:
            req = auth_profile.api_call(
                path='{}/ids.json'.format(ids_type),
                params={'user_id': self.twitter_id, 'cursor': cursor},
                )
            data = req.json()
            ids = ids + data['ids']
            if data['next_cursor']:
                cursor = data['next_cursor']
            else:
                done = True
        if ids_type == 'followers':
            print("SAVING FOLLOWERS")
            self.followers_ids = ids
        elif ids_type == 'friends':
            print("SAVING FRIENDS")
            self.friends_ids = ids
        else:
            print("IDS TYPE?")
            print(ids_type)
        self.save()

    def get_api(self):
        auth = get_tweepy_auth()
        auth.set_access_token(self.oauth_token, self.oauth_token_secret)
        api = tweepy.API(auth)
        return api

    def refresh_full_data(self, auth_profile, max_sec_stale=0):
        if self.last_full_refresh:
            delta = timezone.now() - self.last_full_refresh
            if delta.seconds <= max_sec_stale:
                return
        self.refresh_show_data(auth_profile=auth_profile,
                               max_sec_stale=max_sec_stale)
        self.update_ids(ids_type='followers', auth_profile=auth_profile)
        self.update_ids(ids_type='friends', auth_profile=auth_profile)
        self.last_full_refresh = timezone.now()
        self.save()


class TwitterRelationship(models.Model):
    followed = models.ForeignKey(TwitterProfile, related_name='followed')
    follower = models.ForeignKey(TwitterProfile, related_name='follower')

    class Meta:
        unique_together = ('followed', 'follower',)

    def __str__(self):
        return('{} --> {}'.format(
            self.follower.username, self.followed.username))


class TwitterQuery(models.Model):
    querent = models.ForeignKey(TwitterProfile, related_name='querent_query')
    authorizer = models.ForeignKey(
        TwitterProfile, related_name='authorizer_query')
    path = models.TextField()
    params = JSONField(default={})
    timestamp = models.DateTimeField(auto_now_add=True)
