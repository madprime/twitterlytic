from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models

import tweepy

from .utils import get_tweepy_auth

User = get_user_model()


class TwitterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    twitter_id = models.BigIntegerField()
    username = models.CharField(max_length=15)
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=140, blank=True)
    oauth_token = models.CharField(max_length=50, blank=True)
    oauth_token_secret = models.CharField(max_length=45, blank=True)
    friends_ids = ArrayField(models.BigIntegerField(), null=True)
    followers_ids = ArrayField(models.BigIntegerField(), null=True)

    def get_api(self):
        auth = get_tweepy_auth()
        auth.set_access_token(self.oauth_token, self.oauth_token_secret)
        api = tweepy.API(auth)
        return api

    def refresh_twitter_data(self, api=None):
        if not api:
            api = self.get_api()
        user = api.get_user(self.twitter_id)
        self.username = user.screen_name
        self.name = user.name
        self.description = user.description
        self.followers_ids = user.followers_ids()
        self.friends_ids = api.friends_ids(self.twitter_id)
