from django.conf import settings

import tweepy


class RateExceededError(Exception):
    pass


def get_tweepy_auth():
    return tweepy.OAuthHandler(
        settings.TWEEPY_CONSUMER_TOKEN, settings.TWEEPY_CONSUMER_SECRET)


def get_ratio(counts):
    try:
        ratio = (
            (counts['male'] + counts['mostly_male']) /
            (counts['female'] + counts['mostly_female']))
    except ZeroDivisionError:
        ratio = 0
    return ratio
