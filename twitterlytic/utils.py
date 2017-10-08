from django.conf import settings

import tweepy


def get_tweepy_auth():
    return tweepy.OAuthHandler(
        settings.TWEEPY_CONSUMER_TOKEN, settings.TWEEPY_CONSUMER_SECRET)


def get_tweepy_api(oauth_token, oauth_token_secret):
    auth = get_tweepy_auth()
    auth.request_token = {'oauth_token': oauth_token,
                          'oauth_token_secret': oauth_token_secret}
    (token, token_secret) = auth.get_access_token(oauth_token_secret)
    auth.set_access_token(token, token_secret)
    api = tweepy.API(auth)
    return api
