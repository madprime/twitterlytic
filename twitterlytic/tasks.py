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
from .utils import RateExceededError

# Set up logging.
logger = logging.getLogger(__name__)


@shared_task
def get_followers_and_friends(target_id, authed_id, num_submit=0):
    """
    Retrieve all follower profiles for a Twitter profile.
    """
    target_profile = TwitterProfile.objects.get(id=target_id)
    auth_profile = TwitterProfile.objects.get(id=authed_id)
    api = auth_profile.get_api()

    try:
        target_profile.refresh_full_data(auth_profile=auth_profile)
    except RateExceededError:
        num_submit += 1
        get_followers_and_friends.apply_async(
            kwargs={'target_id': target_id,
                    'authed_id': authed_id,
                    'num_submit': num_submit},
            countdown=900)
        print("Cap hit, waiting 15 minutes...")
        return

    print('Retrieving followers for {}...'.format(target_profile.show_data['screen_name']))
    for twitter_id in target_profile.followers_ids:
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=twitter_id)
        try:
            profile.refresh_show_data(auth_profile=auth_profile,
                                      max_sec_stale=86400)
            TwitterRelationship.objects.get_or_create(
                followed=target_profile, follower=profile)
        except RateExceededError:
            num_submit += 1
            get_followers_and_friends.apply_async(
                kwargs={'target_id': target_id,
                        'authed_id': authed_id,
                        'num_submit': num_submit},
                countdown=900)
            print('Cap hit, waiting 15 minutes...')
            return

    print('Retrieving friends for {}...'.format(target_profile.show_data['screen_name']))
    for twitter_id in target_profile.friends_ids:
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=twitter_id)
        try:
            profile.refresh_show_data(auth_profile=auth_profile,
                                      max_sec_stale=86400)
            TwitterRelationship.objects.get_or_create(
                followed=profile, follower=target_profile)
        except RateExceededError:
            num_submit += 1
            get_followers_and_friends.apply_async(
                kwargs={'target_id': target_id,
                        'authed_id': authed_id,
                        'num_submit': num_submit},
                countdown=900)
            print("Cap hit, waiting 15 minutes...")
            return
    print("Done with analysis for {}".format(target_profile.show_data['screen_name']))
