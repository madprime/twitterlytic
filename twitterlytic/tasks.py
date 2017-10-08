"""
Asynchronous tasks using celery.
"""
from __future__ import absolute_import

# import json
import logging
# import os
# import shutil
# import tempfile
# import textwrap
# from urllib2 import HTTPError

# import arrow
from celery import shared_task
# from django.utils import lorem_ipsum
# import requests

import tweepy

from .models import TwitterProfile, TwitterRelationship


# Set up logging.
logger = logging.getLogger(__name__)


@shared_task
def test_task():
    print("TEST TASK CALLED AND EXECUTED")


@shared_task
def get_followers_and_friends(target_id, authed_id, num_submit=0):
    """
    Retrieve all follower profiles for a Twitter profile.
    """
    target_profile = TwitterProfile.objects.get(id=target_id)
    auth_profile = TwitterProfile.objects.get(id=authed_id)
    api = auth_profile.get_api()

    try:
        target_profile.refresh_twitter_data(api=api)
    except tweepy.error.RateLimitError:
        num_submit += 1
        get_followers_and_friends.apply_async(
            kwargs={'target_id': target_id,
                    'authed_id': authed_id,
                    'num_submit': num_submit},
            countdown=900)
        print("Cap hit, waiting 15 minutes...")
        return

    print('Username: {}'.format(target_profile.username))
    print('Followers IDs: {}'.format(target_profile.followers_ids))
    for twitter_id in target_profile.followers_ids:
        print(twitter_id)
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=twitter_id)
        try:
            profile.refresh_twitter_data(api=api, max_sec_stale=86400)
            TwitterRelationship.objects.get_or_create(
                followed=target_profile, follower=profile)
            print("Done with {}...".format(profile.username))
        except tweepy.error.RateLimitError:
            num_submit += 1
            get_followers_and_friends.apply_async(
                kwargs={'target_id': target_id,
                        'authed_id': authed_id,
                        'num_submit': num_submit},
                countdown=900)
            print("Cap hit, waiting 15 minutes...")
            return

    print('Username: {}'.format(target_profile.username))
    print('Followers IDs: {}'.format(target_profile.followers_ids))
    for twitter_id in target_profile.friends_ids:
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=twitter_id)
        try:
            profile.refresh_twitter_data(api=api, max_sec_stale=86400)
            TwitterRelationship.objects.get_or_create(
                followed=profile, follower=target_profile)
            print("Done with {}...".format(profile.username))
        except tweepy.error.RateLimitError:
            num_submit += 1
            get_followers_and_friends.apply_async(
                kwargs={'target_id': target_id,
                        'authed_id': authed_id,
                        'num_submit': num_submit},
                countdown=900)
            print("Cap hit, waiting 15 minutes...")
            return
