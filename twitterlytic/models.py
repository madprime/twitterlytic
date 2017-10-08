from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone

import gender_guesser.detector as gender
import tweepy

from .utils import get_tweepy_auth

User = get_user_model()
gender_guesser = gender.Detector()

GENDER_CHOICES = (
    ('unknown', 'unrecognized'),
    ('andy', 'either'),
    ('male', 'male (probably)'),
    ('female', 'female (probably)'),
    ('mostly_male', 'male (maybe)'),
    ('mostly_female', 'female (maybe)'),
)


def guess_gender(name, description):
    if 'she/her' in description:
        return 'female'
    elif 'he/him' in description:
        return 'male'
    elif 'they/them' in description:
        return 'andy'
    return gender_guesser.get_gender(name.split()[0].title())


class TwitterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    twitter_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=15)
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=200, blank=True)
    oauth_token = models.CharField(max_length=50, blank=True)
    oauth_token_secret = models.CharField(max_length=45, blank=True)
    friends_ids = ArrayField(models.BigIntegerField(), null=True)
    followers_ids = ArrayField(models.BigIntegerField(), null=True)
    followers = models.ManyToManyField(
        'self', through='TwitterRelationship', symmetrical=False,
        through_fields=('followed', 'follower'),)
    last_refresh = models.DateTimeField(null=True)
    gender = models.CharField(
        max_length=13,
        choices=GENDER_CHOICES,
        default='unknown',
    )

    def serialized(self):
        return {
            'twitter_id': self.twitter_id,
            'username': self.username,
            'name': self.name,
            'description': self.description,
            'gender': self.gender,
        }

    def get_api(self):
        auth = get_tweepy_auth()
        auth.set_access_token(self.oauth_token, self.oauth_token_secret)
        api = tweepy.API(auth)
        return api

    def refresh_twitter_data(self, api=None, max_sec_stale=0):
        if self.last_refresh:
            delta = timezone.now() - self.last_refresh
            if delta.seconds <= max_sec_stale:
                return
        if not api:
            api = self.get_api()
        user = api.get_user(self.twitter_id)
        self.username = user.screen_name
        self.name = user.name
        self.description = user.description
        self.gender = guess_gender(user.name, user.description)
        try:
            self.followers_ids = user.followers_ids()
            self.friends_ids = api.friends_ids(self.twitter_id)
        except tweepy.error.TweepError:
            pass
        self.last_refresh = timezone.now()
        self.save()


class TwitterRelationship(models.Model):
    followed = models.ForeignKey(TwitterProfile, related_name='followed')
    follower = models.ForeignKey(TwitterProfile, related_name='follower')

    class Meta:
        unique_together = ('followed', 'follower',)
