# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-10-30 12:56
from __future__ import unicode_literals

from django.db import migrations
from os.path import dirname, abspath, join
import csv

BASE_DIR = dirname(abspath(__file__))


def forwards_func(apps, schema_editor):
    '''
    Reloads the organization type combo
    '''
    Dropdown = apps.get_model('noclook', 'Dropdown')
    Choice = apps.get_model('noclook', 'Choice')

    orgtype_dropname = 'organization_types'

    # delete the already present options
    orgdropdown, created = \
        Dropdown.objects.get_or_create(name=orgtype_dropname)
    Choice.objects.filter(dropdown=orgdropdown).delete()

    # add them again from the csv file
    with open(join(BASE_DIR, 'common_dropdowns.csv')) as f:
        for line in csv.DictReader(f):
            dropdown_name = line['dropdown']

            if dropdown_name == orgtype_dropname:
                dropdown, created = \
                    Dropdown.objects.get_or_create(name=dropdown_name)
                value = line['value']
                name = line['name'] or value
                if value:
                    Choice.objects.get_or_create(dropdown=dropdown,
                                                 value=value,
                                                 name=name)

def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('noclook', '0017_auth_default_groups_20191023_0823'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]