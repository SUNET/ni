# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from apps.noclook.schema.core import *

class Port(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })
    port_type = NIChoiceField()
    description = NIStringField()
    parent = NISingleRelationField(field_type=NodeHandler, rel_name='Has', rel_method='get_parent')
    connected_to = NIListField(type_args=(lambda: NodeHandler,), rel_name='Connected_to', rel_method='get_relations')

    class NIMetaType:
        ni_type = 'Port'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Cable(NIObjectType):
    name = NIStringField(type_kwargs={ 'required': True })
    cable_type = NIChoiceField()
    description = NIStringField()
    # providers = NIListField(type_args=(lambda: Provider,), rel_name='Provides', rel_method='get_relations')
    ports = NIListField(type_args=(lambda: Port,), rel_name='Connected_to', rel_method='get_outgoing_relations')

    class NIMetaType:
        ni_type = 'Cable'
        ni_metatype = NIMETA_PHYSICAL
        context_method = sriutils.get_network_context


class Host(NIObjectType):
    '''
    A host in the SRI system
    '''
    name = NIStringField(type_kwargs={ 'required': True })
    operational_state = NIStringField(type_kwargs={ 'required': True })
    os = NIStringField()
    os_version = NIStringField()
    vendor = NIStringField()
    backup = NIStringField()
    managed_by = NIStringField()
    ip_addresses = IPAddr()
    description = NIStringField()
    responsible_group = NIStringField()
    support_group = NIStringField()
    security_class = NIStringField()
    security_comment = NIStringField()

    def resolve_ip_addresses(self, info, **kwargs):
        '''Manual resolver for the ip field'''
        return self.get_node().data.get('ip_addresses', None)

    class NIMetaType:
        ni_type = 'Host'
        ni_metatype = NIMETA_LOGICAL
        context_method = sriutils.get_network_context
