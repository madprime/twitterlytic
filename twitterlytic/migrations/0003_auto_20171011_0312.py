# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-11 03:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('twitterlytic', '0002_auto_20171010_2204'),
    ]

    operations = [
        migrations.AlterField(
            model_name='twitterprofile',
            name='username',
            field=models.CharField(max_length=20),
        ),
    ]
