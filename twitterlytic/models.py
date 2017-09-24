from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

import tweepy

User = get_user_model()


class TwitterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    twitter_id = models.CharField(max_length=10)
    username = models.CharField(max_length=15)
    oauth_token = models.CharField(max_length=50, blank=True)
    oauth_token_secret = models.CharField(max_length=45, blank=True)

    def get_api(self):
        auth = tweepy.OAuthHandler(
            settings.TWEEPY_CONSUMER_TOKEN, settings.TWEEPY_CONSUMER_SECRET)
        oauth_token = self.oauth_token
        verifier = self.oauth_token_secret
        request_token = {'oauth_token': oauth_token,
                         'oauth_token_secret': verifier}
        auth.request_token = request_token
        api = tweepy.API(auth)
        return api
