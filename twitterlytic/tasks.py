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
from django.conf import settings
from django.utils import timezone
# from django.utils import lorem_ipsum
# import requests

from .models import TwitterProfile, TwitterRelationship, GENDER_CHOICES
from .utils import get_ratio, RateExceededError

# Set up logging.
logger = logging.getLogger(__name__)


def bulk_profile_update(ids_list, auth_profile, target, reltype=None):
    print('Bulk profile update for {}s of {}...'.format(
        reltype, target.username))
    assert reltype in ['friend', 'follower']
    bulk_data = auth_profile.api_call(
        path='users/lookup.json',
        params={'user_id': ','.join([str(x) for x in ids_list])}).json()
    for data in bulk_data:
        profile = TwitterProfile.objects.get(twitter_id=data['id'])
        profile.refresh_show_data(data=data, auth_profile=auth_profile)
        if reltype == 'friend':
            TwitterRelationship.objects.get_or_create(
                followed=profile, follower=target)
        elif reltype == 'follower':
            TwitterRelationship.objects.get_or_create(
                followed=target, follower=profile)


def update_connections(target_profile, auth_profile, reltype=None):
    assert reltype in ['friend', 'follower']
    print('Retrieving {}s for {}...'.format(reltype, target_profile.username))
    ids_list = []

    if reltype == 'friend':
        twitter_id_list = target_profile.friends_ids
        old_rels = TwitterRelationship.objects.filter(follower=target_profile)
        for rel in old_rels:
            if rel.followed.twitter_id not in target_profile.friends_ids:
                rel.delete()

    elif reltype == 'follower':
        twitter_id_list = target_profile.followers_ids
        old_rels = TwitterRelationship.objects.filter(followed=target_profile)
        for rel in old_rels:
            if rel.follower.twitter_id not in target_profile.followers_ids:
                rel.delete()

    for twitter_id in twitter_id_list:
        profile, _ = TwitterProfile.objects.get_or_create(
            twitter_id=twitter_id)
        if ((not profile.last_show_refresh) or
                (profile.last_show_refresh - timezone.now()).seconds > 0):
            ids_list.append(twitter_id)
        if len(ids_list) == 100:
            bulk_profile_update(ids_list=ids_list,
                                auth_profile=auth_profile,
                                target=target_profile,
                                reltype=reltype)
            ids_list = []
    if ids_list:
        bulk_profile_update(ids_list=ids_list,
                            auth_profile=auth_profile,
                            target=target_profile,
                            reltype=reltype)
    ids_list = []


@shared_task
def get_followers_and_friends(target_id, authed_id, num_submit=0):
    """
    Retrieve all connected profiles for a Twitter profile.
    """
    target_profile = TwitterProfile.objects.get(id=target_id)
    if num_submit > settings.TWITTERLYTIC_MAX_RESUBMIT:
        print("Max analyses ({}) hit for {}. Aborting.".format(
            settings.TWITTERLYTIC_MAX_RESUBMIT,
            target_profile.show_data['screen_name']))
        return
    auth_profile = TwitterProfile.objects.get(id=authed_id)

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

    try:
        update_connections(target_profile, auth_profile, reltype='friend')
        update_connections(target_profile, auth_profile, reltype='follower')
    except RateExceededError:
        num_submit += 1
        get_followers_and_friends.apply_async(
            kwargs={'target_id': target_id,
                    'authed_id': authed_id,
                    'num_submit': num_submit},
            countdown=900)
        print("Cap hit, waiting 15 minutes...")
        return

    following = TwitterRelationship.objects.filter(follower=target_profile)
    following_genders = list(following.values_list(
            'followed__gender', flat=True))
    following_counts = {g: following_genders.count(g) for g in
                        dict(GENDER_CHOICES).keys()}
    following_ratio = get_ratio(following_counts)
    target_profile.friends_ratio = following_ratio
    print("Updating following ratio for {}: {}".format(
        target_profile.show_data['screen_name'], following_ratio))

    followers = TwitterRelationship.objects.filter(followed=target_profile)
    followers_genders = list(followers.values_list(
        'follower__gender', flat=True))
    followers_counts = {g: followers_genders.count(g) for g in
                        dict(GENDER_CHOICES).keys()}
    followers_ratio = get_ratio(followers_counts)
    target_profile.followers_ratio = followers_ratio
    print("Updating followers ratio for {}: {}".format(
        target_profile.show_data['screen_name'], followers_ratio))

    target_profile.save()

    print("Done with analysis for {}".format(
        target_profile.show_data['screen_name']))
