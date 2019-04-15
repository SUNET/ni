# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from .core import *
from ..models import *

def resolve_roles_list(self, info, **kwargs):
    rel_method = 'get_outgoing_relations'
    rel_name = 'Is'
    neo4jnode = self.get_node()
    relations = getattr(neo4jnode, rel_method)()
    roles = relations.get(rel_name)

    # this may be the worst way to do it, but it's just for a PoC
    handle_id_list = []
    for role in roles:
        role = role['node']
        role_id = role.data.get('handle_id')
        handle_id_list.append(role_id)

    ret = NodeHandle.objects.filter(handle_id__in=handle_id_list)

    return ret

class RoleType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })

class ContactType(NIObjectType):
    name = NIObjectField(type_kwargs={ 'required': True })
    first_name = NIObjectField(type_kwargs={ 'required': True })
    last_name = NIObjectField(type_kwargs={ 'required': True })
    title = NIObjectField()
    salutation = NIObjectField()
    contact_type = NIObjectField()
    phone = NIObjectField()
    mobile = NIObjectField()
    email = NIObjectField()
    other_email = NIObjectField()
    PGP_fingerprint = NIObjectField()
    is_roles = NIObjectField(field_type=graphene.List, type_args=(RoleType,), rel_name='Is', rel_method='get_outgoing_relations')
    #is_roles2 = NIObjectField(field_type=graphene.List, type_args=(RoleType,), manual_resolver=resolve_roles_list)
