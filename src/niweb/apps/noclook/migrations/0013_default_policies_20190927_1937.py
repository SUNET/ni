# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2019-09-27 19:37
from __future__ import unicode_literals

from django.db import migrations
from vakt import Policy, ALLOW_ACCESS, DENY_ACCESS

import apps.noclook.vakt.rules as srirules
import apps.noclook.vakt.utils as sriutils
import uuid
import vakt.rules as vakt_rules


def forwards_func(apps, schema_editor):
    # get storage and guard
    storage, guard = sriutils.get_vakt_storage_and_guard()

    # create policies using storage instead
    Context = apps.get_model('noclook', 'Context')
    AuthzAction = apps.get_model('noclook', 'AuthzAction')

    # iterate over all existent contexts and authzactions
    # and create policies for each of them
    all_contexts = Context.objects.all()
    rw_authzactions = AuthzAction.objects.filter(name__in=(
        sriutils.READ_AA_NAME,
        sriutils.WRITE_AA_NAME,
    ))

    # add read and write policies
    for context in all_contexts:
        for authzaction in rw_authzactions:
            policy = Policy(
                uuid.uuid4(),
                actions=[vakt_rules.Eq(authzaction.name)],
                resources=[srirules.BelongsContext(context)],
                subjects=[srirules.HasAuthAction(authzaction, context)],
                context={ 'module': srirules.ContainsElement(context.name) },
                effect=ALLOW_ACCESS,
                description='Automatically created policy'
            )
            storage.add(policy)

    # add admin policies
    admin_aa = AuthzAction.objects.get(name=sriutils.ADMIN_AA_NAME)
    for context in all_contexts:
        policy = Policy(
            uuid.uuid4(),
            actions=[vakt_rules.Eq(admin_aa.name)],
            resources=[vakt_rules.Any()],
            subjects=[srirules.HasAuthAction(admin_aa, context)],
            context={ 'module': srirules.ContainsElement(context.name) },
            effect=ALLOW_ACCESS,
            description='Automatically created policy'
        )
        storage.add(policy)

def backwards_func(apps, schema_editor):
    # delete all stored policies
    DjPolicy = apps.get_model('djangovakt', 'Policy')
    DjPolicy.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('djangovakt', '0001_initial'),
        ('noclook', '0012_authzaction_context_groupcontextauthzaction_nodehandlecontext'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
