# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-10-07 17:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0014_default_context_20191002_1159'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodehandle',
            name='contexts',
            field=models.ManyToManyField(through='noclook.NodeHandleContext', to='noclook.Context'),
        ),
    ]
