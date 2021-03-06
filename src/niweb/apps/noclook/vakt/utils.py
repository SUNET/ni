# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import logging

from apps.noclook.models import NodeHandle, AuthzAction, \
                            GroupContextAuthzAction, NodeHandleContext, Context
from djangovakt.storage import DjangoStorage
from vakt import Guard, RulesChecker, Inquiry

READ_AA_NAME  = 'read'
WRITE_AA_NAME = 'write'
ADMIN_AA_NAME = 'admin'
LIST_AA_NAME = 'list'

NETWORK_CTX_NAME = 'Network'
COMMUNITY_CTX_NAME = 'Community'
CONTRACTS_CTX_NAME = 'Contracts'


logger = logging.getLogger(__name__)

def trim_readable_queryset(qs, user):
    '''
    This function trims a Queryset of nodes to keep only those the user has
    rights to read
    '''
    logger.debug('Authorizing user to read a set of nodes')

    # get all readable contexts for this user
    user_groups = user.groups.all()
    read_aa = get_read_authaction()

    gcaas = GroupContextAuthzAction.objects.filter(
        group__in=user.groups.all(),
        authzprofile=read_aa
    )

    readable_contexts = []
    for gcaa in gcaas:
        readable_contexts.append(gcaa.context)

    # queryset only will match nodes that the user can read
    if readable_contexts:
        # the hard way
        readable_ids = NodeHandleContext.objects.filter(
            context__in=readable_contexts
        ).values_list('nodehandle_id', flat=True)

        qs = qs.filter(handle_id__in=readable_ids)
    else:
        # the user doesn't have rights to any context
        qs.none()

    return qs


def get_vakt_storage_and_guard():
    storage = DjangoStorage()
    guard = Guard(storage, RulesChecker())

    return storage, guard


def get_authaction_by_name(name, aamodel=AuthzAction):
    authzaction = aamodel.objects.get(name=name)
    return authzaction


def get_read_authaction(aamodel=AuthzAction):
    return get_authaction_by_name(READ_AA_NAME, aamodel)


def get_write_authaction(aamodel=AuthzAction):
    return get_authaction_by_name(WRITE_AA_NAME, aamodel)


def get_admin_authaction(aamodel=AuthzAction):
    return get_authaction_by_name(ADMIN_AA_NAME, aamodel)


def get_list_authaction(aamodel=AuthzAction):
    return get_authaction_by_name(LIST_AA_NAME, aamodel)


def get_context_by_name(name, cmodel=Context):
    try:
        context = cmodel.objects.get(name=name)
    except:
        context = None

    return context


def get_network_context(cmodel=Context):
    return get_context_by_name(NETWORK_CTX_NAME, cmodel)


def get_community_context(cmodel=Context):
    return get_context_by_name(COMMUNITY_CTX_NAME, cmodel)


def get_contracts_context(cmodel=Context):
    return get_context_by_name(CONTRACTS_CTX_NAME, cmodel)


def get_default_context(cmodel=Context):
    return get_community_context(cmodel)


def get_all_contexts(cmodel=Context):
    contexts = dict(
        community = get_community_context(cmodel),
        network = get_network_context(cmodel),
        contracts = get_contracts_context(cmodel),
    )

    return contexts


def authorize_aa_resource(user, handle_id, get_aa_func):
    '''
    This function checks if an user is authorized to do a specific action over
    a node specified by its handle_id. It forges an inquiry and check it against
    vakt's guard.
    '''
    ret = False # deny by default

    # get storage and guard
    storage, guard = get_vakt_storage_and_guard()

    # get authaction
    authaction = get_aa_func()

    # get contexts for this resource
    nodehandle = NodeHandle.objects.prefetch_related('contexts').get(handle_id=handle_id)
    contexts = get_nh_contexts(nodehandle)

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction.name,
        resource=nodehandle,
        subject=user,
        context={'module': contexts}
    )

    ret = guard.is_allowed(inquiry)

    return ret


def authorice_read_resource(user, handle_id):
    logger.debug('Authorizing user to read a node with id {}'.format(handle_id))
    return authorize_aa_resource(user, handle_id, get_read_authaction)


def authorice_write_resource(user, handle_id):
    logger.debug('Authorizing user to write a node with id {}'.format(handle_id))
    return authorize_aa_resource(user, handle_id, get_write_authaction)


def authorize_aa_operation(user, context, get_aa_func):
    '''
    This function authorizes an action within a particular context, it checks
    if the user can perform that action within this SRI module
    '''
    ret = False # deny by default

    # get storage and guard
    storage, guard = get_vakt_storage_and_guard()

    # get authaction
    authaction = get_aa_func()

    # forge read resource inquiry
    inquiry = Inquiry(
        action=authaction.name,
        resource=None,
        subject=user,
        context={'module': (context.name,)}
    )

    ret = guard.is_allowed(inquiry)

    return ret


def authorize_read_module(user, context):
    '''
    This function authorizes the read operation on a resource within a defined
    context, it checks if the user can read objects from this SRI module
    '''
    logger.debug('Authorizing user to read a node within the module {}'\
        .format(context.name))
    return authorize_aa_operation(user, context, get_read_authaction)


def authorize_create_resource(user, context):
    '''
    This function authorizes the creation of a resource within a particular
    context, it checks if the user can write within this SRI module
    '''
    logger.debug('Authorizing user to create a node within the module {}'\
        .format(context.name))
    return authorize_aa_operation(user, context, get_write_authaction)


def authorize_admin_module(user, context):
    '''
    This function checks if the user can perform admin actions inside a module
    '''
    logger.debug('Authorizing user to admin the module {}'\
        .format(context.name))
    return authorize_aa_operation(user, context, get_admin_authaction)


def authorize_list_module(user, context):
    '''
    This function checks if the user can perform admin actions inside a module
    '''
    logger.debug('Authorizing user to admin the module {}'\
        .format(context.name))
    return authorize_aa_operation(user, context, get_list_authaction)


def authorize_superadmin(user, cmodel=Context):
    '''
    This function checks if the user can perform super admin actions
    '''
    logger.debug('Authorizing user {} as a superadmin'.format(user.username))

    is_superadmin = True
    all_contexts = cmodel.objects.all()

    for context in all_contexts:
        if not authorize_aa_operation(user, context, get_admin_authaction):
            is_superadmin = False
            break

    return is_superadmin


def user_is_admin(user):
    nh_contexts = get_all_contexts()
    is_admin = False

    for name, nh_context in nh_contexts.items():
        if authorize_admin_module(user, nh_context):
            return True

    return is_admin


def get_ids_user_canread(user):
    user_groups = user.groups.all()
    read_aa = get_read_authaction()

    gcaas = GroupContextAuthzAction.objects.filter(
        group__in=user_groups,
        authzprofile=read_aa
    )

    readable_contexts = []
    for gcaa in gcaas:
        readable_contexts.append(gcaa.context)

    ret = []

    if readable_contexts:
        readable_ids = NodeHandleContext.objects.filter(
            context__in=readable_contexts
        ).values_list('nodehandle_id', flat=True)

        for id in readable_ids:
            if id not in ret:
                ret.append(id)

    return ret


def get_nh_contexts(nh):
    return [ c.name for c in nh.contexts.all() ]


def get_nh_named_contexts(nh):
    return [ { 'context_name': c } for c in get_nh_contexts(nh) ]


def get_aaction_context_group(auth_action, context):
    groupctxaa = None
    groupctxaa_f = GroupContextAuthzAction.objects.filter(
        authzprofile=auth_action, context=context)

    if groupctxaa_f:
        groupctxaa = groupctxaa_f.first()

    return groupctxaa.group


def edit_aaction_context_user(auth_action, context, user, add=False):
    # get the relation between the authorized action and the context
    # to get the user group
    group = get_aaction_context_group(auth_action, context)

    if group:
        # add user to group
        group_users = group.user_set.all()

        if add and user not in group_users:
            group.user_set.add(user)

        if not add and user in group_users:
            group.user_set.remove(user)

        group.save()


def set_nodehandle_context(context, nh):
    # set new context
    NodeHandleContext.objects.get_or_create(context=context, nodehandle=nh)


def set_nodehandle_contexts(contexts, nh):
    # delete unrelated NodeHandleContext
    NodeHandleContext.objects.filter(nodehandle=nh)\
        .exclude(context__in=contexts).delete()

    for context in contexts:
        set_nodehandle_context(context, nh)
