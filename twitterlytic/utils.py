from django.conf import settings

import tweepy


class RateExceededError(Exception):
    pass


def get_tweepy_auth():
    return tweepy.OAuthHandler(
        settings.TWEEPY_CONSUMER_TOKEN, settings.TWEEPY_CONSUMER_SECRET)
