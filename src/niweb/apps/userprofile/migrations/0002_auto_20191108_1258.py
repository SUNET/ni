# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-11-08 12:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userprofile', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='landing_page',
            field=models.CharField(choices=[('network', 'Network'), ('services', 'Services'), ('community', 'Community')], default='community', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='view_community',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='view_network',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='view_services',
            field=models.BooleanField(default=True),
        ),
    ]
