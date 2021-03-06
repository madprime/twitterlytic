# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-11-26 02:32
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('twitterlytic', '0003_auto_20171011_0312'),
    ]

    operations = [
        migrations.CreateModel(
            name='TwitterQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.TextField()),
                ('params', django.contrib.postgres.fields.jsonb.JSONField(default={})),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('authorizer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='authorizer_query', to='twitterlytic.TwitterProfile')),
                ('querent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='querent_query', to='twitterlytic.TwitterProfile')),
            ],
        ),
    ]
